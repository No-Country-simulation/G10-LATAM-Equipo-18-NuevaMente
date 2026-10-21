# -*- coding: utf-8 -*-
"""
test_executive_summary.py

Purpose:
    Offline tests for the "Executive Summary" output format. They verify that
    the summary covers the whole document, that every paragraph cites its
    sources with numbered references, that the reference list holds one line
    per number, that the text is written in the selected language, that no
    placeholder content is published and that the notices shown when the
    summary cannot be produced are correct.

    The LLM is replaced by a double, so the tests never hit the network.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.labels import (
    canonical_format_key,
    language_display_name,
    resolve_language_code,
    summary_message,
)
from app.schemas.adaptation import AdaptationRequest
from app.services.langgraph_orchestrator import LangGraphOrchestrator
from app.services.summary_composer import compose_summary_with_citations


class _FakeLlm:
    """LLM double that returns canned responses and records the prompts."""

    def __init__(self, responses):
        self.responses = responses
        self.prompts = []
        self.system_instructions = []

    @property
    def is_available(self) -> bool:
        return True

    def generate(self, prompt, system_instruction=None, json_output=False, model_name=None):
        self.prompts.append(prompt)
        self.system_instructions.append(system_instruction or "")
        index = min(len(self.prompts) - 1, len(self.responses) - 1)
        return json.dumps(self.responses[index], ensure_ascii=False)


class _NoWaitGuard:
    """Rate guard double without pacing between calls."""

    def should_attempt(self, provider, model=None) -> bool:
        return True

    def wait_for_slot(self, provider, model=None) -> None:
        return None

    def record_success(self, provider, model=None) -> None:
        return None

    def record_failure(self, provider, model=None) -> None:
        return None


def _request(language: str = "es", quantity: int = 8) -> AdaptationRequest:
    return AdaptationRequest(
        documento_titulo="Bitcoin: A Peer-to-Peer Electronic Cash System",
        documento_contenido="Contenido del documento de prueba.",
        perfil_destinatario="Desarrollador",
        formato_salida="Resumen Ejecutivo",
        nicho_sector="General",
        nivel_detalle="Didactico",
        cantidad_objetivo=quantity,
        idioma_salida=language,
    )


def _topics() -> list:
    """Topics holding one excerpt per section, each with its own chunk id."""
    return [
        {
            "topic": "Bitcoin",
            "concept": "Bitcoin",
            "target_items": 8,
            "chunk_id": "parent_0",
            "page": None,
            "section": "Documento completo",
            "breadcrumb": "",
            "context": "contexto",
            "excerpts": [
                {
                    "chunk_id": "parent_1",
                    "section": "1. Introducción",
                    "breadcrumb": "Bitcoin > 1. Introducción",
                    "page": 2,
                    "text": "Bitcoin es un sistema de efectivo electrónico entre pares.",
                },
                {
                    "chunk_id": "parent_5",
                    "section": "3. Proof of Work",
                    "breadcrumb": "Bitcoin > 3. Proof of Work",
                    "page": 4,
                    "text": "La prueba de trabajo protege el libro mayor distribuido.",
                },
            ],
        }
    ]


def _orchestrator_with_llm(payload) -> tuple:
    orchestrator = LangGraphOrchestrator()
    fake = _FakeLlm(payload)
    orchestrator._provider_map = {"groq": fake, "gemini": fake, "openrouter": fake}
    return orchestrator, fake


# ---------------------------------------------------------------------------
# Reference list
# ---------------------------------------------------------------------------

def test_summary_paragraphs_carry_reference_numbers():
    """Every paragraph ends with the numbers of the sections it comes from."""
    items = [
        {
            "punto_clave": "Bitcoin permite pagos directos entre pares",
            "impacto_negocio": "Reduce la dependencia de intermediarios",
            "fuentes": [
                {"chunk_id": "parent_1", "seccion": "1. Introducción", "pagina": 2},
                {"chunk_id": "parent_5", "seccion": "3. Proof of Work", "pagina": 4},
            ],
        },
        {
            "punto_clave": "La prueba de trabajo protege el libro mayor",
            "impacto_negocio": "Sostiene la confianza en la red",
            "fuentes": [{"chunk_id": "parent_5", "seccion": "3. Proof of Work", "pagina": 4}],
        },
    ]

    text = compose_summary_with_citations(items, "Bitcoin", "es")

    assert "Bitcoin permite pagos directos entre pares." in text
    assert "[1][2]" in text
    # The same reference can be repeated in different paragraphs.
    assert text.count("[2]") >= 2


def test_summary_reference_list_has_one_line_per_number():
    """The reference list holds the document title once and one line per number."""
    items = [
        {
            "punto_clave": "Punto con dos secciones",
            "impacto_negocio": "Impacto",
            "fuentes": [
                {"chunk_id": "parent_1", "seccion": "1. Introducción", "pagina": 2},
                {"chunk_id": "parent_7", "seccion": "1. Introducción", "pagina": 5},
            ],
        }
    ]

    text = compose_summary_with_citations(items, "Bitcoin", "es")
    body, references = text.split("\n\n", 1)

    assert body.strip().endswith("[1][2]")
    reference_lines = [line for line in references.splitlines() if line.strip()]
    assert reference_lines[0] == "Fuentes"
    # The document title appears once, as the general source.
    assert reference_lines[1] == "Bitcoin"
    # Same section with different pages: two different numbers.
    assert reference_lines[2] == "[1] 1. Introducción (p. 2)"
    assert reference_lines[3] == "[2] 1. Introducción (p. 5)"


def test_summary_without_verifiable_content_is_empty():
    """Without content there is no summary text at all."""
    assert compose_summary_with_citations([], "Bitcoin", "es") == ""

    # A point without an identifiable source is kept, but without a reference.
    items = [{"punto_clave": "Punto", "impacto_negocio": "Impacto", "fuentes": []}]
    text = compose_summary_with_citations(items, "Bitcoin", "es")
    assert text == "Punto. Impacto."
    assert "Fuentes" not in text


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def test_summary_prompt_carries_every_section_excerpt():
    """The generation prompt shows the excerpts of the whole document."""
    responses = [
        [
            {
                "punto_clave": "Punto generado",
                "impacto_negocio": "Impacto generado",
                "fuentes": [{"chunk_id": "parent_1", "seccion": "1. Introducción", "extracto": "..."}],
            }
        ]
    ]
    orchestrator, fake = _orchestrator_with_llm(responses)

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        items = orchestrator._generate_summary_items(
            request=_request(),
            doc_title="Bitcoin",
            topics=_topics(),
            target=1,
            target_language="es",
        )

    assert len(items) == 1
    prompt = fake.prompts[0]
    assert "parent_1" in prompt
    assert "parent_5" in prompt
    assert "1. Introducción" in prompt
    assert "3. Proof of Work" in prompt


def test_summary_prompt_uses_the_selected_language():
    """The prompt asks for the selected language, never a hardcoded one."""
    responses = [[{"punto_clave": "Punto", "impacto_negocio": "Impacto", "fuentes": []}]]
    orchestrator, fake = _orchestrator_with_llm(responses)

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        orchestrator._generate_summary_items(
            request=_request(language="pt"),
            doc_title="Bitcoin",
            topics=_topics(),
            target=1,
            target_language="pt",
        )

    prompt = fake.prompts[0]
    assert "Portuguese" in prompt
    assert "Spanish" not in prompt
    assert "Portuguese" in fake.system_instructions[0]


def test_summary_prompt_does_not_mention_the_sector():
    """The selected sector never reaches the summary prompt."""
    responses = [[{"punto_clave": "Punto", "impacto_negocio": "Impacto", "fuentes": []}]]
    orchestrator, fake = _orchestrator_with_llm(responses)

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        orchestrator._generate_summary_items(
            request=_request(),
            doc_title="Bitcoin",
            topics=_topics(),
            target=1,
            target_language="es",
        )

    assert "General" not in fake.prompts[0]
    assert "General" not in fake.system_instructions[0]


def test_summary_requests_more_points_until_the_target_is_reached():
    """When the model returns fewer points, the missing ones are requested again."""
    responses = [
        [
            {
                "punto_clave": "Primero",
                "impacto_negocio": "Uno",
                "fuentes": [{"chunk_id": "parent_1", "seccion": "1. Introducción"}],
            }
        ],
        [
            {
                "punto_clave": "Segundo",
                "impacto_negocio": "Dos",
                "fuentes": [{"chunk_id": "parent_5", "seccion": "3. Proof of Work"}],
            }
        ],
    ]
    orchestrator, fake = _orchestrator_with_llm(responses)

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        items = orchestrator._generate_summary_items(
            request=_request(),
            doc_title="Bitcoin",
            topics=_topics(),
            target=2,
            target_language="es",
        )

    assert len(items) == 2
    assert len(fake.prompts) == 2


def test_summary_never_returns_placeholder_content():
    """When the model cannot deliver points, no placeholder block is produced."""
    orchestrator, _ = _orchestrator_with_llm([[]])

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        items = orchestrator._generate_summary_items(
            request=_request(),
            doc_title="Bitcoin",
            topics=_topics(),
            target=3,
            target_language="es",
        )

    assert items == []


def test_summary_asks_again_for_the_sections_not_covered():
    """A follow-up round asks for the sections no point cites yet."""
    responses = [
        [
            {
                "punto_clave": "Punto de la introduccion",
                "impacto_negocio": "Impacto de la introduccion",
                "fuentes": [{"chunk_id": "parent_1", "seccion": "1. Introducción"}],
            }
        ],
        [
            {
                "punto_clave": "Punto de la prueba de trabajo",
                "impacto_negocio": "Impacto de la prueba de trabajo",
                "fuentes": [{"chunk_id": "parent_5", "seccion": "3. Proof of Work"}],
            }
        ],
    ]
    orchestrator, fake = _orchestrator_with_llm(responses)

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        items = orchestrator._generate_summary_items(
            request=_request(),
            doc_title="Bitcoin",
            topics=_topics(),
            target=2,
            target_language="es",
        )

    assert len(items) == 2
    assert len(fake.prompts) == 2
    # The follow-up round only shows the section that was still missing.
    assert "parent_5" in fake.prompts[1]
    assert "parent_1" not in fake.prompts[1]
    assert "SECTIONS NOT COVERED YET" in fake.prompts[1]


def test_summary_sources_receive_section_and_page():
    """The citation metadata is completed with the location of the excerpt."""
    responses = [
        [
            {
                "punto_clave": "Punto generado",
                "impacto_negocio": "Impacto generado",
                "fuentes": [{"chunk_id": "parent_5", "extracto": "..."}],
            }
        ]
    ]
    orchestrator, _ = _orchestrator_with_llm(responses)

    with patch("app.services.pipeline_stages.get_llm_guard", return_value=_NoWaitGuard()):
        items = orchestrator._generate_summary_items(
            request=_request(),
            doc_title="Bitcoin",
            topics=_topics(),
            target=1,
            target_language="es",
        )

    source = items[0]["fuentes"][0]
    assert source["seccion"] == "3. Proof of Work"
    assert source["pagina"] == 4
    assert source["breadcrumb"] == "Bitcoin > 3. Proof of Work"


# ---------------------------------------------------------------------------
# Published content
# ---------------------------------------------------------------------------

def test_published_summary_drops_placeholder_blocks():
    """Placeholder blocks never reach the published summary."""
    orchestrator, _ = _orchestrator_with_llm([])
    items = [
        {
            "punto_clave": "Punto real",
            "impacto_negocio": "Impacto real",
            "fuentes": [{"chunk_id": "parent_1", "seccion": "1. Introducción", "pagina": 2}],
        },
        {
            "punto_clave": "Aspectos estratégicos y operativos de Bitcoin.",
            "impacto_negocio": "Garantiza la continuidad operativa en el sector General.",
            "fuentes": [{"chunk_id": "parent_0", "seccion": "Documento completo"}],
            "es_fallback": True,
        },
    ]

    content = orchestrator._format_adapted_content(
        request=_request(),
        doc_title="Bitcoin",
        items=items,
        effective_count=1,
        target_language="es",
    )

    assert "Punto real" in content.executive_summary
    assert "Aspectos estratégicos" not in content.executive_summary
    assert "sector General" not in content.executive_summary
    assert len(content.items) == 1


def test_published_summary_reports_the_failure_when_empty():
    """An empty summary explains what happened instead of publishing filler."""
    orchestrator, _ = _orchestrator_with_llm([])

    content = orchestrator._format_adapted_content(
        request=_request(language="pt"),
        doc_title="Bitcoin",
        items=[],
        effective_count=0,
        target_language="pt",
    )

    assert "Não foi possível gerar um resumo" in content.executive_summary
    assert content.items == []


def test_other_formats_keep_their_content():
    """Formats that already work are not affected by the summary changes."""
    orchestrator, _ = _orchestrator_with_llm([])
    request = AdaptationRequest(
        documento_titulo="Arquitectura de Microservicios",
        documento_contenido="Contenido",
        perfil_destinatario="Desarrollador",
        formato_salida="Flashcards",
        nicho_sector="General",
        nivel_detalle="Didactico",
        cantidad_objetivo=2,
    )
    items = [{"frente": "Pregunta", "dorso": "Respuesta", "fuentes": []}]

    content = orchestrator._format_adapted_content(
        request=request,
        doc_title="Arquitectura de Microservicios",
        items=items,
        effective_count=1,
        target_language="es",
    )

    assert content.items == items
    assert not content.executive_summary


# ---------------------------------------------------------------------------
# Notices
# ---------------------------------------------------------------------------

def _formatter_state(items, requested, language="es"):
    return {
        "request": _request(language=language, quantity=requested),
        "doc_title": "Bitcoin",
        "audited_items": items,
        "effective_target": requested,
        "target_quantity": requested,
        "capacity_warning": None,
        "target_language": language,
        "evaluation": None,
        "key_concepts": [],
        "prerequisites": [],
        "document_id": None,
        "tracer": None,
        "nodes_executed": [],
        "revision_count": 0,
    }


def _run_formatter(state):
    orchestrator, _ = _orchestrator_with_llm([])
    queue = MagicMock()
    queue.enqueue_content_job.return_value = {"job_id": "job", "bucket": "b", "objeto_id": "o"}
    queue.process_job.return_value = True

    with patch(
        "app.services.storage_queue_service.StorageQueueService.get_instance", return_value=queue
    ), patch("app.services.langgraph_orchestrator.PDFExportService"):
        return orchestrator._node_formatter(state)["final_response"]


def test_formatter_reports_a_general_notice_when_the_summary_is_empty():
    """An empty summary produces a short general notice."""
    response = _run_formatter(_formatter_state([], 8))

    assert response.metadata.general_notice
    assert response.metadata.general_notice != summary_message("empty_detail", "es")
    assert response.adapted_content.executive_summary


def test_formatter_reports_a_partial_summary():
    """A summary with fewer paragraphs than requested is reported."""
    items = [
        {
            "punto_clave": "Bitcoin permite pagos directos entre pares sin intermediarios",
            "impacto_negocio": "Reduce la dependencia de plataformas de pago tradicionales",
            "fuentes": [{"chunk_id": "parent_1", "seccion": "1. Introducción", "verificado": True}],
        }
    ]

    response = _run_formatter(_formatter_state(items, 8))

    assert response.metadata.general_notice is None
    assert response.metadata.quantity_warning
    assert "1" in response.metadata.quantity_warning


def test_formatter_keeps_other_formats_untouched():
    """No general notice is raised for formats that are not the summary."""
    state = _formatter_state([], 8)
    state["request"] = AdaptationRequest(
        documento_titulo="Arquitectura",
        documento_contenido="Contenido",
        perfil_destinatario="Desarrollador",
        formato_salida="Flashcards",
        nicho_sector="General",
        nivel_detalle="Didactico",
        cantidad_objetivo=8,
    )

    response = _run_formatter(state)

    assert response.metadata.general_notice is None


# ---------------------------------------------------------------------------
# Language helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("es", "es"),
        ("en", "en"),
        ("pt", "pt"),
        ("Spanish", "es"),
        ("English", "en"),
        ("Portuguese", "pt"),
        ("Portugu\u00e9s", "pt"),
        ("pt-BR", "pt"),
        (None, "es"),
    ],
)
def test_language_resolution(raw, expected):
    """Any language label is normalized into a supported code."""
    assert resolve_language_code(raw) == expected


def test_language_display_names():
    """Prompts receive the English name of the selected language."""
    assert language_display_name("es") == "Spanish"
    assert language_display_name("en") == "English"
    assert language_display_name("pt") == "Portuguese"


def test_canonical_format_key():
    """Every label of the executive summary resolves to the same key."""
    assert canonical_format_key("Resumen Ejecutivo") == "executive_summary"
    assert canonical_format_key("resumen") == "executive_summary"
    assert canonical_format_key("Executive Summary") == "executive_summary"
    assert canonical_format_key("Flashcards") == "flashcards"


def test_summary_messages_follow_the_target_language():
    """Notices are written in the selected language."""
    assert "No se pudo" in summary_message("empty_short", "es")
    assert "could not be generated" in summary_message("empty_short", "en")
    assert "Não foi possível" in summary_message("empty_short", "pt")
    assert summary_message("sources_header", "es") == "Fuentes"
    assert summary_message("sources_header", "en") == "Sources"
    assert summary_message("sources_header", "pt") == "Fontes"
