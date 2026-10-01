"""
test_diagnose_adaptation_script.py

Pruebas unitarias para backend/scripts/diagnose_adaptation.py
Verifica que el script de diagnóstico retorne FALLÓ cuando se inyectan plantillas fijas,
duplicados o scores fijos, y APROBADO cuando las salidas difieren y son dinámicas.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Inserción de ruta backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.diagnose_adaptation import run_adaptation_diagnostics
from app.schemas.adaptation import AdaptationResponse, ResponseMetadata, QualityEvaluation, AdaptedContent, OCIStorageResult

def _make_mock_response(title: str, text_content: str, items_count: int, grounding_score: float, prompt_hash: str, origin: str = "llm"):
    items = [
        {
            "frente": f"Concepto {i+1} de {title}",
            "dorso": f"Explicación detallada {i+1} ({text_content})",
            "fuentes": [{"chunk_id": f"c{i+1}", "extracto": "fuente"}]
        }
        for i in range(items_count)
    ]
    meta = ResponseMetadata(
        profile_applied="Principiante",
        format_generated="Flashcards",
        niche_sector="Salud",
        detail_level="Didactico",
        quantity_level="Breve",
        requested_items=items_count,
        generated_items=items_count,
        estimated_study_time_minutes=10,
        key_concepts=["Java", "Spring"],
        prerequisites=["OOP"],
        prompt_hash=prompt_hash,
        origin=origin,
        fallback_used=False
    )
    qual = QualityEvaluation(
        source_grounding_score=grounding_score,
        pedagogical_clarity="Alta",
        observations="OK"
    )
    content = AdaptedContent(
        title=title,
        contextualized_introduction="Intro",
        items=items
    )
    oci = OCIStorageResult(bucket="bkt", object_id="obj-1", upload_status="success")
    return AdaptationResponse(status="exito", metadata=meta, adapted_content=content, quality_evaluation=qual, oci_storage=oci)


@patch("scripts.diagnose_adaptation.AgentOrchestrator")
@patch("scripts.diagnose_adaptation.PdfParserService")
@patch("scripts.diagnose_adaptation.IngesterService")
@patch("scripts.diagnose_adaptation.HybridRAGService")
@patch("scripts.diagnose_adaptation.GraphRAGService")
def test_diagnose_script_detects_fixed_template_failure(mock_graph, mock_hybrid, mock_ingester, mock_parser, mock_orch_cls):
    """Verifica que el script devuelva FALLÓ cuando las respuestas contienen plantillas fijas o scores hardcodeados."""
    mock_parser.return_value.parse_pdf_to_markdown.return_value = ("Markdown de Java", {"paginas": 10, "caracteres": 5000, "caracteres_por_pagina": 500})
    mock_graph.return_value.build_concept_dag.return_value = (None, ["Java"], ["OOP"])
    
    # Inyectar respuesta fija con frase prohibida "Aumenta la eficiencia"
    resp_fixed = _make_mock_response("Título Fijo", "Aumenta la eficiencia en fintech", 10, 0.98, "hash_123")
    mock_orch_cls.return_value.run_pipeline.return_value = resp_fixed
    
    passed, failures, report_md = run_adaptation_diagnostics(save_report=False)
    
    assert passed is False
    assert len(failures) > 0
    assert any("Aumenta la eficiencia" in f or "idénticos" in f or "0.98" in f for f in failures)


@patch("scripts.diagnose_adaptation.AgentOrchestrator")
@patch("scripts.diagnose_adaptation.PdfParserService")
@patch("scripts.diagnose_adaptation.IngesterService")
@patch("scripts.diagnose_adaptation.HybridRAGService")
@patch("scripts.diagnose_adaptation.GraphRAGService")
def test_diagnose_script_passes_on_dynamic_outputs(mock_graph, mock_hybrid, mock_ingester, mock_parser, mock_orch_cls):
    """Verifica que el script devuelva APROBADO cuando las respuestas son dinámicas, variadas y sin patrones prohibidos."""
    mock_parser.return_value.parse_pdf_to_markdown.return_value = ("Texto completo del PDF sobre Java y Spring Boot", {"paginas": 10, "caracteres": 5000, "caracteres_por_pagina": 500})
    mock_graph.return_value.build_concept_dag.return_value = (None, ["Java", "Spring"], ["OOP"])

    responses = [
        _make_mock_response("Flashcards Principiante", "Conceptos básicos de clases y objetos en Java", 10, 0.912, "hash_a"),
        _make_mock_response("Flashcards Desarrollador", "Optimización de garbage collector y hilos", 30, 0.895, "hash_b"),
        _make_mock_response("Tutorial Líder Técnico", "Arquitectura de microservicios con Spring Cloud Gateway", 12, 0.943, "hash_c"),
        _make_mock_response("Resumen Ejecutivo", "Métricas de adopción y rendimiento de JVM", 5, 0.925, "hash_d"),
        _make_mock_response("Flashcards Principiante Caché", "Conceptos básicos de clases y objetos en Java", 10, 0.912, "hash_a", origin="cache"),
        _make_mock_response("Flashcards 25", "Patrones de diseño GoF en Java", 25, 0.901, "hash_e"),
        _make_mock_response("Quiz 15", "Evaluación de concurrencia en Java", 15, 0.934, "hash_f")
    ]
    
    # Hacer que run_pipeline devuelva una respuesta diferente para cada combinación
    mock_orch_cls.return_value.run_pipeline.side_effect = responses
    
    passed, failures, report_md = run_adaptation_diagnostics(save_report=False)
    
    assert passed is True
    assert len(failures) == 0
    assert "STATUS: **APROBADO**" in report_md
