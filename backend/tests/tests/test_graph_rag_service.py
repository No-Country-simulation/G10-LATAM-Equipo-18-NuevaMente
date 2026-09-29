import pytest
from unittest.mock import patch, MagicMock
from app.services.graph_rag_service import GraphRAGService

@patch("app.services.graph_rag_service.GeminiClient")
def test_graph_rag_gemini_success(mock_gemini_class):
    service = GraphRAGService()
    
    # Mocking la respuesta de Gemini
    mock_gemini_class.return_value.generate_content.return_value = '{"concepts": ["NodeA"], "relationships": []}'
    service.gemini_client = mock_gemini_class.return_value

    json_data, concepts, pre_reqs = service.build_concept_dag("Este es un texto sobre NodeA.")
    
    assert len(concepts) > 0
    assert "NodeA" in concepts

@patch("app.services.graph_rag_service.EmbeddingService")
@patch("app.services.graph_rag_service.GeminiClient")
def test_graph_rag_fallback_jina(mock_gemini_class, mock_embedding_class):
    service = GraphRAGService()
    
    # Hacemos que Gemini arroje excepción para forzar el fallback
    mock_gemini_class.return_value.generate_content.side_effect = Exception("API Falló")
    service.gemini_client = mock_gemini_class.return_value
    
    # Mockeamos EmbeddingService de Jina
    mock_jina_instance = MagicMock()
    mock_jina_instance.embed_text.return_value = [0.1, 0.2]
    mock_jina_instance.embed_batch.return_value = [[0.1, 0.2], [0.9, 0.1]]
    mock_embedding_class.return_value = mock_jina_instance
    
    texto_largo = "Hola mundo. Programacion Avanzada en Python y OCI."
    graph, concepts, pre_reqs = service.build_concept_dag(texto_largo)
    
    # El fallback no arroja excepción, devuelve conceptos extraídos
    assert len(concepts) > 0
