import pytest
from unittest.mock import patch, MagicMock
from app.services.hybrid_rag_service import HybridRAGService

def test_rrf_scoring_logic():
    """Testea que la fusión RRF combina correctamente listas léxicas y semánticas"""
    mock_emb = MagicMock()
    service = HybridRAGService(embedding_service=mock_emb)
    
    # Simula chunks
    lexical = [{"id": "chunk1", "score": 0.9}, {"id": "chunk2", "score": 0.5}]
    dense = [{"id": "chunk2", "score": 0.8}, {"id": "chunk1", "score": 0.4}]
    
    rrf_results = service._rrf(lexical, dense, k=60)
    
    # Ambos chunks deben estar en el resultado
    assert len(rrf_results) == 2
    # El chunk 1 estaba primero en lex y segundo en dense.
    # El chunk 2 estaba segundo en lex y primero en dense.
    assert rrf_results[0]["id"] in ["chunk1", "chunk2"]
    # Deberían tener la llave "rrf_score" añadida.
    assert "rrf_score" in rrf_results[0]

@patch("app.services.hybrid_rag_service.cohere.ClientV2")
def test_hybrid_reranking_cohere(mock_cohere):
    """Testea que Cohere se aplique a los documentos padre (Reranking) y funcione sin return_documents"""
    mock_emb = MagicMock()
    service = HybridRAGService(embedding_service=mock_emb)
    service.co_client = mock_cohere.return_value
    
    # Mockear la respuesta de rerank
    mock_response = MagicMock()
    mock_result1 = MagicMock()
    mock_result1.index = 1
    mock_result1.relevance_score = 0.99
    
    mock_result2 = MagicMock()
    mock_result2.index = 0
    mock_result2.relevance_score = 0.12
    
    mock_response.results = [mock_result1, mock_result2]
    service.co_client.rerank.return_value = mock_response
    
    # Ejecutamos retrieve (mockeando bm25 y dense internamente, solo nos importa el paso final de rerank)
    # Es más fácil testear la inyección directa al bloque de reranking
    # O mockear _rrf y _map_to_parents
    with patch.object(service, '_rrf', return_value=[{"parent_id": "p1"}, {"parent_id": "p2"}]):
        with patch.object(service, '_map_to_parents', return_value=[{"id": "p1", "content": "Texto1"}, {"id": "p2", "content": "Texto2"}]):
            
            with patch.object(service.embedding_service, 'embed_text', return_value=[0.1]*10):
                final_docs = service.retrieve_top_passages(
                    query="Hola",
                    child_chunks=[{"id": "c1", "content": "...", "parent_id": "p1"}, {"id": "c2", "content": "...", "parent_id": "p2"}],
                    parent_chunks=[{"id": "p1", "content": "Texto1"}, {"id": "p2", "content": "Texto2"}]
                )
            
                assert len(final_docs) == 2
                service.co_client.rerank.assert_called_once()
                # Verificar que el error return_documents no está en la llamada
                kwargs = service.co_client.rerank.call_args[1]
                assert "return_documents" not in kwargs
