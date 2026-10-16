"""
test_quiz_option_shuffle.py

Purpose:
    Regression tests for the quiz answer-position shuffle and the source
    verification flag. Historically the LLM and the deterministic fallback put
    the correct option first, so answers clustered in A/B; these tests lock in
    that options are randomized while `respuesta_correcta` keeps pointing at the
    same text.

Input:
    In-memory quiz items and an AdaptationRequest; no network or API keys.

Output:
    Assertions only.
"""

import random

from app.schemas.adaptation import AdaptationRequest, RagFuente
from app.services.pipeline_stages import PipelineStages


def _quiz_item(correct_first: bool = True):
    options = ["Correcta", "Distractor B", "Distractor C", "Distractor D"]
    if not correct_first:
        random.shuffle(options)
    return {
        "pregunta": "¿Cuál es la respuesta correcta?",
        "opciones": list(options),
        "respuesta_correcta": "Correcta",
        "justificacion": "Porque sí.",
        "fuentes": [{"chunk_id": "parent_1", "extracto": "Correcta"}],
    }


def test_shuffle_preserves_options_and_correct_answer():
    stages = PipelineStages()
    item = _quiz_item()
    original = set(item["opciones"])

    stages._shuffle_quiz_options([item])

    assert set(item["opciones"]) == original, "shuffle must not add/drop options"
    assert item["respuesta_correcta"] in item["opciones"]
    assert item["respuesta_correcta"] == "Correcta"


def test_shuffle_spreads_correct_positions():
    random.seed(1234)
    stages = PipelineStages()
    items = [_quiz_item() for _ in range(200)]

    stages._shuffle_quiz_options(items)

    positions = {it["opciones"].index(it["respuesta_correcta"]) for it in items}
    assert len(positions) >= 3, f"correct answers should spread across options, got {positions}"


def test_shuffle_skips_items_without_valid_options():
    stages = PipelineStages()

    no_options = {"pregunta": "x", "respuesta_correcta": "y"}
    correct_absent = {
        "pregunta": "x",
        "opciones": ["a", "b"],
        "respuesta_correcta": "z",
    }

    stages._shuffle_quiz_options([no_options, correct_absent])

    assert no_options == {"pregunta": "x", "respuesta_correcta": "y"}
    assert correct_absent["opciones"] == ["a", "b"]


def test_format_adapted_content_shuffles_quiz_items():
    random.seed(7)
    stages = PipelineStages()
    request = AdaptationRequest(
        title="Doc",
        content="Contenido",
        recipient_profile="Principiante",
        output_format="Quiz",
    )
    items = [_quiz_item() for _ in range(5)]

    adapted = stages._format_adapted_content(
        request=request,
        doc_title="Doc",
        items=items,
        effective_count=len(items),
        target_language="Spanish",
    )

    for raw in adapted.items:
        assert set(raw["opciones"]) == {"Correcta", "Distractor B", "Distractor C", "Distractor D"}
        assert raw["respuesta_correcta"] in raw["opciones"]

    assert adapted.quizzes, "quiz items must also be produced"
    for quiz in adapted.quizzes:
        assert quiz.correct_answer in quiz.options


def test_ragfuente_keeps_verification_flag():
    fuente = RagFuente(chunk_id="parent_1", extracto="texto", verificado=True)

    assert fuente.verificado is True
    assert fuente.model_dump(by_alias=True)["verificado"] is True
