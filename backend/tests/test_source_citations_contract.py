"""
test_source_citations_contract.py

Purpose:
    Contract tests for the source view shared by generation, critic and repair,
    plus the citation rules the prompts are supposed to enforce.

    These tests were RED against commit ac7833d and now guard the fixes:

      - The critic and repair stages receive the whole cited chunk through a
        shared boundary-safe context window.
      - Non-holistic coverage plans expose per-chunk excerpts with real ids.
      - The consolidated batch never forces one chunk_id for every item.
      - The critic payload excludes quiz distractors from factual auditing.
      - A negative-stem quiz is not rejected when its cited chunk supports the
        correct answer.
"""

import json

import pytest

from app.core.config import settings
from app.schemas.adaptation import AdaptationRequest
from app.services.coverage_planner import CoveragePlanner
from app.services.pipeline_stages import PipelineStages


class _RecordingLLM:
    """Fake provider that records prompts and returns a valid critic payload."""

    is_available = True

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt, system_instruction=None, json_output=False, model_name=None):
        self.prompts.append(prompt)
        return json.dumps(
            {
                "overall_grounding_score": 1.0,
                "pedagogical_clarity": "High",
                "observations": "ok",
                "item_evaluations": [
                    {"index": 0, "is_grounded": True, "clarity": "High", "issues": []}
                ],
            }
        )


class _NoopGuard:
    def should_attempt(self, *args, **kwargs):
        return True

    def wait_for_slot(self, *args, **kwargs):
        return None

    def record_success(self, *args, **kwargs):
        return None

    def record_failure(self, *args, **kwargs):
        return None


def _request() -> AdaptationRequest:
    return AdaptationRequest(
        documento_titulo="Documento",
        documento_contenido="Contenido",
        perfil_destinatario="Estudiantes",
        formato_salida="Quiz",
    )


def _stages_with_recorder(monkeypatch) -> tuple[PipelineStages, _RecordingLLM]:
    stages = PipelineStages()
    fake = _RecordingLLM()
    stages._provider_map = {"testprovider": fake}
    monkeypatch.setattr(
        settings,
        "CRITIC_CASCADE",
        [{"provider": "testprovider", "model": None}],
    )
    monkeypatch.setattr(
        "app.services.pipeline_stages.get_llm_guard",
        lambda: _NoopGuard(),
    )
    return stages, fake


def _long_chunk_with_tail_marker() -> tuple[str, str]:
    """Content longer than the 400-char critic budget, with a unique tail."""
    marker = "MARCADOR_QUE_SOLO_APARECE_AL_FINAL_DEL_CHUNK"
    content = "Contenido inicial del fragmento. " + ("Relleno tecnico suficiente. " * 25) + marker
    assert len(content) > 400
    return content, marker


def test_critic_receives_the_whole_cited_chunk(monkeypatch) -> None:
    """The critic must see the same chunk the writer used, not a 400-char cut."""
    stages, fake = _stages_with_recorder(monkeypatch)
    content, marker = _long_chunk_with_tail_marker()

    item = {
        "_gid": "ground_0",
        "pregunta": "¿Qué describe el fragmento?",
        "respuesta_correcta": "Un contenido técnico.",
        "justificacion": "El fragmento lo describe.",
        "grounded": True,
        "fuentes": [{"chunk_id": "parent_0", "verificado": True}],
    }

    stages._evaluate_quality_with_critic(
        request=_request(),
        generated_items=[item],
        passages=[{"id": "parent_0", "content": content}],
        fallback_score=1.0,
    )

    assert fake.prompts, "the critic LLM must be called"
    assert marker in fake.prompts[0], (
        "the critic prompt is missing the tail of the cited chunk; "
        "the source was truncated to 400 characters"
    )


def test_repair_receives_the_whole_cited_chunk(monkeypatch) -> None:
    """The repair stage must not rewrite against a different, shorter source view."""
    stages, fake = _stages_with_recorder(monkeypatch)
    stages.router.get_model_cascade = lambda fmt: [{"provider": "testprovider", "model": None}]
    content, marker = _long_chunk_with_tail_marker()

    item = {
        "_gid": "ground_0",
        "pregunta": "¿Qué describe el fragmento?",
        "respuesta_correcta": "Un contenido técnico.",
        "justificacion": "El fragmento lo describe.",
        "fuentes": [{"chunk_id": "parent_0", "verificado": False}],
    }

    stages._stage_repair_items(
        request=_request(),
        items_to_repair=[(0, item, ["cita no verificada"])],
        passages=[{"id": "parent_0", "content": content}],
    )

    assert fake.prompts, "the repair LLM must be called"
    assert marker in fake.prompts[0], (
        "the repair prompt is missing the tail of the cited chunk; "
        "the source was truncated to 500 characters"
    )


def test_non_holistic_plans_expose_citable_excerpts() -> None:
    """Every generation strategy must expose real chunk ids, not only the summary."""
    chunks = [
        {
            "id": "parent_0",
            "title": "Sección uno",
            "breadcrumb": "Documento > Sección uno",
            "content": ("Contenido de la sección uno. " * 40),
            "metadata": {"page_number": 1},
        },
        {
            "id": "parent_1",
            "title": "Sección dos",
            "breadcrumb": "Documento > Sección dos",
            "content": ("Contenido de la sección dos. " * 40),
            "metadata": {"page_number": 2},
        },
    ]

    plan = CoveragePlanner().plan(
        parent_chunks=chunks,
        output_format="quiz",
        requested_items=10,
    )

    assert plan.sections, "the planner must produce sections"
    for section in plan.sections:
        assert section.excerpts, (
            f"section '{section.section_title}' has no excerpts; the writer "
            "cannot cite anything but the primary chunk"
        )
        assert all(excerpt.get("chunk_id") for excerpt in section.excerpts)


def test_consolidated_batch_does_not_force_one_chunk_id_for_every_item(monkeypatch) -> None:
    """A batch spanning two sections must not tell every item to cite c1."""
    stages, fake = _stages_with_recorder(monkeypatch)
    stages.router.get_model_cascade = lambda fmt: [{"provider": "testprovider", "model": None}]
    stages.router.get_cascade_order = lambda fmt: ["testprovider"]

    topics = [
        {
            "topic": "Sección uno",
            "chunk_id": "c1",
            "page": 1,
            "section": "Sección uno",
            "breadcrumb": "Documento > Sección uno",
            "context": "Contexto de la sección uno.",
            "target_items": 3,
        },
        {
            "topic": "Sección dos",
            "chunk_id": "c2",
            "page": 2,
            "section": "Sección dos",
            "breadcrumb": "Documento > Sección dos",
            "context": "Contexto de la sección dos.",
            "target_items": 2,
        },
    ]

    stages._stage_batch_generators(
        request=_request(),
        doc_title="Documento",
        topics=topics,
        passages=[],
        target=5,
        target_language="Spanish",
    )

    prompt = fake.prompts[0]
    if '"chunk_id": "c1"' in prompt:
        assert '"chunk_id": "c2"' in prompt, (
            "the consolidated prompt hardcodes c1 as the citation for every "
            "item; items about section two cannot cite c2 correctly"
        )


def test_critic_does_not_audit_unlabelled_quiz_distractors(monkeypatch) -> None:
    """Distractors are intentionally false; the critic must not treat them as claims."""
    stages, fake = _stages_with_recorder(monkeypatch)

    item = {
        "_gid": "ground_0",
        "pregunta": "¿Qué hace HTTPS?",
        "opciones": [
            "Cifra las comunicaciones usando TLS.",
            "Invalida todas las políticas de seguridad de la red.",
            "Solo funciona en entornos heredados sin certificados.",
            "Reemplaza por completo el uso de firewalls.",
        ],
        "respuesta_correcta": "Cifra las comunicaciones usando TLS.",
        "justificacion": "HTTPS cifra las comunicaciones usando TLS.",
        "grounded": True,
        "fuentes": [{"chunk_id": "parent_0", "verificado": True}],
    }

    stages._evaluate_quality_with_critic(
        request=_request(),
        generated_items=[item],
        passages=[
            {
                "id": "parent_0",
                "content": "El protocolo HTTPS cifra las comunicaciones usando TLS.",
            }
        ],
        fallback_score=1.0,
    )

    prompt = fake.prompts[0]
    distractor = "Invalida todas las políticas de seguridad de la red."
    if distractor in prompt:
        assert "distractor" in prompt.lower() or "no validar" in prompt.lower(), (
            "the critic receives quiz distractors as unlabelled factual claims; "
            "they must be excluded or explicitly marked as non-validatable"
        )


def test_negative_stem_quiz_is_not_rejected_by_the_lexical_gate(monkeypatch) -> None:
    """A 'which is NOT...' question is not a factual negation against the source."""
    stages, _ = _stages_with_recorder(monkeypatch)
    passages = [
        {
            "id": "parent_0",
            "content": "El protocolo HTTPS cifra las comunicaciones usando TLS.",
        }
    ]
    item = {
        "pregunta": "¿Cuál de las siguientes NO es una función de HTTPS?",
        "opciones": [
            "Cifrar las comunicaciones usando TLS.",
            "Reemplazar el uso de firewalls.",
            "Eliminar la necesidad de certificados.",
            "Desactivar la autenticación del servidor.",
        ],
        "respuesta_correcta": "Cifrar las comunicaciones usando TLS.",
        "justificacion": "HTTPS cifra las comunicaciones usando TLS.",
        "fuentes": [{"chunk_id": "parent_0"}],
    }

    verified = stages._stage_verify_grounding([item], passages)

    assert verified[0]["grounded"] is True, (
        "the anti-negation gate rejected a supported quiz item because the "
        "question stem contains 'NO'; the gate must only inspect factual claims"
    )
