"""
test_batch_generation_prompts.py

Purpose:
    Regression tests for the prompt assembly in PipelineStages._stage_batch_generators.

    Both generation routes (the consolidated batch and the per-topic batch) render
    the format prompt with str.format(), and every format prompt declares
    {chunk_id} / {page_number}. A route that forgets those placeholders raises
    KeyError('chunk_id') before the LLM is called, which the API surfaces as
    "Content generation error: 'chunk_id'".
"""

import json
from typing import Any, Dict, List

import pytest

from app.schemas.adaptation import AdaptationRequest
from app.services.pipeline_stages import PipelineStages


class RecordingLLM:
    """Stands in for a provider client: records the prompts and returns valid JSON."""

    is_available = True

    def __init__(self) -> None:
        self.prompts: List[str] = []

    def generate(
        self,
        prompt: str,
        system_instruction: str = None,
        json_output: bool = False,
        model_name: str = None,
    ) -> str:
        self.prompts.append(prompt)
        return json.dumps(
            [
                {
                    "frente": "Pregunta",
                    "dorso": "Respuesta",
                    "pista_didactica": "Pista",
                    "fuentes": [
                        {"chunk_id": "c1", "seccion": "S1", "extracto": "extracto"}
                    ],
                }
            ]
        )


def _build_stages() -> PipelineStages:
    """Returns a PipelineStages whose only provider is a recording fake."""
    stages = PipelineStages()
    fake = RecordingLLM()
    # A dedicated provider name keeps the shared rate guard from pacing the test.
    stages._provider_map = {"testprovider": fake}
    stages.router.get_model_cascade = lambda fmt: [{"provider": "testprovider", "model": None}]
    stages.router.get_cascade_order = lambda fmt: ["testprovider"]
    stages.fake_llm = fake
    return stages


def _request(output_format: str) -> AdaptationRequest:
    return AdaptationRequest(
        documento_titulo="Documento",
        documento_contenido="Contenido",
        perfil_destinatario="estudiantes",
        formato_salida=output_format,
    )


def _topics() -> List[Dict[str, Any]]:
    return [
        {
            "topic": "S1",
            "chunk_id": "c1",
            "page": 1,
            "section": "S1",
            "breadcrumb": "Doc > S1",
            "context": "contexto 1",
            "target_items": 3,
        },
        {
            "topic": "S2",
            "chunk_id": "c2",
            "page": 2,
            "section": "S2",
            "breadcrumb": "Doc > S2",
            "context": "contexto 2",
            "target_items": 2,
        },
    ]


@pytest.mark.parametrize("output_format", ["flashcards", "quiz", "tutorial", "guion de clase"])
def test_consolidated_batch_renders_chunk_id(output_format: str) -> None:
    """A consolidated batch (target <= 10, several sections) must not raise KeyError."""
    stages = _build_stages()

    items = stages._stage_batch_generators(
        request=_request(output_format),
        doc_title="Documento",
        topics=_topics(),
        passages=[],
        target=5,
        target_language="Spanish",
    )

    assert items, "the batch stage must return the generated items"
    prompt = stages.fake_llm.prompts[0]
    assert "{chunk_id}" not in prompt, "the {chunk_id} placeholder was left unresolved"
    assert "{page_number}" not in prompt, "the {page_number} placeholder was left unresolved"
    assert '"chunk_id": "c1"' in prompt, "the chunk id was not injected into the prompt"


def test_per_topic_batch_renders_chunk_id() -> None:
    """The per-topic route (target > 10) keeps rendering its own chunk id."""
    stages = _build_stages()

    items = stages._stage_batch_generators(
        request=_request("flashcards"),
        doc_title="Documento",
        topics=_topics(),
        passages=[],
        target=20,
        target_language="Spanish",
    )

    assert items
    prompt = stages.fake_llm.prompts[0]
    assert "{chunk_id}" not in prompt
    assert '"chunk_id": "c1"' in prompt
