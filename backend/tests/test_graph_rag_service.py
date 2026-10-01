import pytest
from unittest.mock import patch, MagicMock
from app.services.graph_rag_service import GraphRAGService

@patch("app.services.graph_rag_service.GeminiClient")
def test_graph_rag_gemini_success(mock_gemini_class):
    service = GraphRAGService()
    
    # Mocking la respuesta de Gemini
    mock_gemini_class.return_value.has_real_key = True
    mock_gemini_class.return_value.generate_content.return_value = '{"concepts": ["NodeA"], "relationships": []}'
    service.gemini_client = mock_gemini_class.return_value

    graph, concepts, pre_reqs = service.build_concept_dag("Este es un texto sobre NodeA.")
    
    assert len(concepts) > 0
    assert "NodeA" in concepts

@patch("app.services.graph_rag_service.GeminiClient")
def test_graph_rag_fallback_heuristics(mock_gemini_class):
    service = GraphRAGService()
    
    # Hacemos que Gemini arroje excepción para forzar la extracción heurística
    mock_gemini_class.return_value.has_real_key = True
    mock_gemini_class.return_value.generate_content.side_effect = Exception("API Falló")
    service.gemini_client = mock_gemini_class.return_value
    
    texto_largo = "# Programación Avanzada\n**Python** y `FastAPI` para arquitectura de software."
    graph, concepts, pre_reqs = service.build_concept_dag(texto_largo)
    
    # El fallback heurístico extrae conceptos estructurados
    assert len(concepts) > 0
