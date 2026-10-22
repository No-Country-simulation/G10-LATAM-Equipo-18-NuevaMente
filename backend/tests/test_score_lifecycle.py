"""
test_score_lifecycle.py

Purpose:
    Regression test for the lifecycle of a critic verdict. The repair node
    must refresh the critic record for every item it rewrites before the graph
    reaches the formatter; otherwise the formatter matches the repaired item by
    `_gid` and reuses the old `verificado_revisor=False`, so a repaired item can
    never recover its anchoring score.

    The test drives repair -> formatter with a deterministic fake repair and
    asserts that a now-supported item is scored as verified.
"""

import pytest

from app.schemas.adaptation import AdaptationRequest, QualityEvaluation
from app.services.langgraph_orchestrator import LangGraphOrchestrator


class _FakeStorageQueue:
    def enqueue_content_job(self, **kwargs):
        return {"job_id": "job-1", "bucket": "test-bucket", "objeto_id": "object-1"}

    def process_job(self, job_id):
        return True

    def save_content_metadata(self, **kwargs):
        return None


def _request() -> AdaptationRequest:
    return AdaptationRequest(
        documento_titulo="Documento",
        documento_contenido="Contenido",
        perfil_destinatario="Estudiantes",
        formato_salida="Quiz",
    )


def test_repaired_item_does_not_keep_a_stale_critic_rejection(monkeypatch) -> None:
    orchestrator = LangGraphOrchestrator()

    content = "El protocolo HTTPS cifra las comunicaciones usando TLS en todas las conexiones."
    passages = [{"id": "parent_0", "content": content}]

    original_item = {
        "_gid": "ground_0",
        "pregunta": "¿Qué hace HTTPS con las comunicaciones?",
        "opciones": [
            "Cifra las comunicaciones usando TLS.",
            "Desactiva la autenticación del servidor.",
            "Reemplaza el uso de firewalls.",
            "Elimina la necesidad de certificados.",
        ],
        "respuesta_correcta": "Cifra las comunicaciones usando TLS.",
        "justificacion": "HTTPS cifra las comunicaciones usando TLS.",
        "fuentes": [{"chunk_id": "parent_0", "verificado": False}],
    }

    repaired_item = {
        **original_item,
        "fuentes": [
            {
                "chunk_id": "parent_0",
                "extracto": "cifra las comunicaciones usando TLS",
                "verificado": False,
            }
        ],
        "repaired": True,
    }

    stale_evaluation = QualityEvaluation(
        source_grounding_score=0.0,
        pedagogical_clarity="Alta",
        observations="Cita no verificada.",
        per_item=[
            {
                "index": 0,
                "_gid": "ground_0",
                "verificado_lexico": False,
                "verificado_revisor": False,
                "origen_verificado": False,
                "claridad": "Alta",
                "issues": ["Cita no verificada."],
                "es_fallback": False,
            }
        ],
    )

    state = {
        "request": _request(),
        "doc_title": "Documento",
        "target_language": "Spanish",
        "audited_items": [original_item],
        "top_passages": passages,
        "all_parent_chunks": passages,
        "evaluation": stale_evaluation,
        "repaired_indices": [],
        "revision_count": 0,
        "max_revisions": 2,
        "effective_target": 1,
        "target_quantity": 1,
        "capacity_warning": None,
        "key_concepts": [],
        "prerequisites": [],
        "document_id": None,
        "topics": [
            {
                "topic": "HTTPS",
                "chunk_id": "parent_0",
                "page": 1,
                "section": "HTTPS",
                "breadcrumb": "Documento > HTTPS",
                "context": content,
                "target_items": 1,
            }
        ],
        "nodes_executed": ["critic"],
    }

    monkeypatch.setattr(
        orchestrator,
        "_stage_repair_items",
        lambda **kwargs: [(0, repaired_item)],
    )
    monkeypatch.setattr(
        "app.services.storage_queue_service.StorageQueueService.get_instance",
        classmethod(lambda cls: _FakeStorageQueue()),
    )

    repaired_state = orchestrator._node_repair(state)
    assert repaired_state["audited_items"], "the repaired item must survive the repair node"

    formatter_state = {**state, **repaired_state, "document_id": None}
    result = orchestrator._node_formatter(formatter_state)
    evaluation = result["final_response"].quality_evaluation

    assert evaluation.per_item[0]["verificado_lexico"] is True
    assert evaluation.per_item[0]["verificado_revisor"] is True, (
        "the formatter reused the stale critic verdict from before the repair"
    )
    assert evaluation.per_item[0]["origen_verificado"] is True
    assert evaluation.source_grounding_score == 1.0, (
        "a repaired and verified item must not be scored as unanchored"
    )
