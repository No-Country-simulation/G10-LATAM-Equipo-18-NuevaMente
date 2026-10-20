"""
test_langgraph_orchestrator.py

Purpose:
    Unit and integration tests for LangGraph multi-agent orchestration.
    Validates graph structure, node transitions, conditional routing,
    self-correction loops, and output compliance with AdaptationResponse.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.core.config import settings
from app.schemas.adaptation import (
    AdaptationRequest,
    AdaptationResponse,
    QualityEvaluation,
)
from app.services.coverage_planner import CoveragePlan, SectionPlan
from app.services.langgraph_orchestrator import LangGraphOrchestrator, AgentState


def test_langgraph_graph_compilation_and_nodes():
    """Validates that LangGraph StateGraph builds with all required agentic nodes."""
    orchestrator = LangGraphOrchestrator()
    graph = orchestrator.graph
    assert graph is not None

    # Inspect compiled graph nodes
    node_names = set(graph.nodes.keys())
    expected_nodes = {
        "planner",
        "writer",
        "deduplicator",
        "grounding_verifier",
        "critic",
        "repair",
        "refiner",
        "formatter",
    }
    assert expected_nodes.issubset(node_names), f"Missing nodes: {expected_nodes - node_names}"


def test_langgraph_conditional_routing_decision():
    """Validates the conditional edge routing logic between critic, repair, refiner, and formatter."""
    orchestrator = LangGraphOrchestrator()

    mock_plan = MagicMock()
    mock_plan.total_capacity = 10

    # Case 1: Items present but none verified, budget available → repair (new priority)
    state_needs_repair: AgentState = {
        "audited_items": [
            {"id": 1, "fuentes": [{"verificado": False}]},
            {"id": 2, "fuentes": [{"verificado": False}]},
        ],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 0,
        "max_revisions": 2,
        "repaired_indices": [],
    }
    route = orchestrator._should_refine_or_complete(state_needs_repair)
    assert route == "repair", "Ungrounded items with budget must route to repair first"

    # Case 2: All items verified, but count below target → refiner
    state_needs_refine: AgentState = {
        "audited_items": [
            {"id": 1, "fuentes": [{"verificado": True}]},
            {"id": 2, "fuentes": [{"verificado": True}]},
        ],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 0,
        "max_revisions": 2,
        "repaired_indices": [],
    }
    route = orchestrator._should_refine_or_complete(state_needs_refine)
    assert route == "refiner"

    # Case 3: Target satisfied, all verified → formatter
    state_satisfied: AgentState = {
        "audited_items": [{"id": i, "fuentes": [{"verificado": True}]} for i in range(5)],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 0,
        "max_revisions": 2,
        "repaired_indices": [],
    }
    route = orchestrator._should_refine_or_complete(state_satisfied)
    assert route == "formatter"

    # Case 4: Revisions exhausted → formatter (even with unverified items)
    state_exhausted: AgentState = {
        "audited_items": [{"id": 1, "fuentes": [{"verificado": False}]}],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 2,
        "max_revisions": 2,
        "repaired_indices": [],
    }
    route = orchestrator._should_refine_or_complete(state_exhausted)
    assert route == "formatter"


@pytest.mark.anyio
async def test_langgraph_pipeline_execution():
    """Validates an asynchronous end-to-end execution of the LangGraph pipeline."""
    orchestrator = LangGraphOrchestrator()

    request = AdaptationRequest(
        documento_titulo="Arquitectura de Microservicios",
        documento_contenido="Los microservicios desacoplan los componentes de una aplicación permitiendo escalado independiente.",
        perfil_destinatario="Principiante",
        formato_salida="Flashcards",
        nicho_sector="General",
        nivel_detalle="Didactico",
        cantidad_objetivo=5,
    )

    passages = [
        {
            "id": "p_0",
            "title": "Arquitectura",
            "content": "Los microservicios desacoplan los componentes de una aplicación.",
            "metadata": {"source_title": "Arquitectura de Microservicios"},
        }
    ]

    response = await orchestrator.run_pipeline(
        request=request,
        top_passages=passages,
        key_concepts=["Microservicios", "Escalado"],
        prerequisites=[],
    )

    assert isinstance(response, AdaptationResponse)
    assert response.status == "exito"
    assert response.metadata.graph_orchestration is True
    assert "planner" in response.metadata.graph_nodes_executed
    assert "writer" in response.metadata.graph_nodes_executed
    assert "critic" in response.metadata.graph_nodes_executed
    assert "formatter" in response.metadata.graph_nodes_executed
    assert len(response.adapted_content.items or []) > 0
    assert response.quality_evaluation.source_grounding_score >= 0.0


def test_repair_router_anti_loop_guarantee():
    """
    Validates that an item already in repaired_indices is NOT re-routed to repair,
    preserving the anti-loop guarantee even if it remains unverified after repair.
    """
    orchestrator = LangGraphOrchestrator()

    mock_plan = MagicMock()
    mock_plan.total_capacity = 10

    # Item 0 is unverified but has already been repaired once
    state_already_repaired: AgentState = {
        "audited_items": [
            {"id": 0, "fuentes": [{"verificado": False}]},
            {"id": 1, "fuentes": [{"verificado": True}]},
        ],
        "effective_target": 2,
        "coverage_plan": mock_plan,
        "revision_count": 1,
        "max_revisions": 2,
        "repaired_indices": [0],  # Item 0 was already repaired
    }
    route = orchestrator._should_refine_or_complete(state_already_repaired)
    # Must NOT route to repair again; no quantity gap either → formatter
    assert route == "formatter", (
        "An item already in repaired_indices must not trigger another repair cycle"
    )


def test_repair_router_routes_to_repair_when_ungrounded():
    """
    Validates that the router directs to 'repair' when unrepaired ungrounded items exist
    and the revision budget has not been exhausted.
    """
    orchestrator = LangGraphOrchestrator()

    mock_plan = MagicMock()
    mock_plan.total_capacity = 5

    state: AgentState = {
        "audited_items": [
            {"id": 0, "fuentes": [{"verificado": False}]},
            {"id": 1, "fuentes": [{"verificado": True}]},
            {"id": 2, "fuentes": [{"verificado": False}]},
        ],
        "effective_target": 3,
        "coverage_plan": mock_plan,
        "revision_count": 0,
        "max_revisions": 2,
        "repaired_indices": [],
    }
    route = orchestrator._should_refine_or_complete(state)
    assert route == "repair", "Two ungrounded items should route to repair when budget allows"
