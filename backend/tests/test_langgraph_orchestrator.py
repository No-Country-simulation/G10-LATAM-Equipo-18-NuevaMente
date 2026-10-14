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
        "refiner",
        "formatter",
    }
    assert expected_nodes.issubset(node_names), f"Missing nodes: {expected_nodes - node_names}"


def test_langgraph_conditional_routing_decision():
    """Validates the conditional edge routing logic between critic, refiner, and formatter."""
    orchestrator = LangGraphOrchestrator()

    mock_plan = MagicMock()
    mock_plan.total_capacity = 10

    # Case 1: Insufficient items, capacity available, revisions remaining -> refiner
    state_needs_refine: AgentState = {
        "audited_items": [{"id": 1}, {"id": 2}],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 0,
        "max_revisions": 2,
    }
    route = orchestrator._should_refine_or_complete(state_needs_refine)
    assert route == "refiner"

    # Case 2: Target satisfied -> formatter
    state_satisfied: AgentState = {
        "audited_items": [{"id": i} for i in range(5)],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 0,
        "max_revisions": 2,
    }
    route = orchestrator._should_refine_or_complete(state_satisfied)
    assert route == "formatter"

    # Case 3: Revisions exhausted -> formatter
    state_exhausted: AgentState = {
        "audited_items": [{"id": 1}],
        "effective_target": 5,
        "coverage_plan": mock_plan,
        "revision_count": 2,
        "max_revisions": 2,
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
