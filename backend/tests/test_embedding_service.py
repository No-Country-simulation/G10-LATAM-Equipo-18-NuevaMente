import pytest
from unittest.mock import patch, MagicMock
from app.services.embedding_service import EmbeddingService

def test_embed_text_gemini_success():
    service = EmbeddingService(provider="gemini")
    with patch.object(service, '_embed_gemini', return_value=[0.1, 0.2, 0.3]) as mock_gemini:
        res = service.embed_text("Hola mundo", is_query=False)
        assert res == [0.1, 0.2, 0.3]
        mock_gemini.assert_called_once_with("Hola mundo", is_query=False)

@patch("app.services.embedding_service.logger")
def test_fallback_cascade_to_jina(mock_logger):
    """Testea que si Gemini falla, pasa a Jina truncando el texto al 50%"""
    service = EmbeddingService(provider="gemini")
    
    # Hacemos que Gemini y Local fallen (o no importan), pero que jina funcione
    with patch.object(service, '_embed_jina_batch', return_value=[[0.5, 0.6]]) as mock_jina:
        # Simulamos que falló Gemini pasándole failed_provider="gemini" directamente
        # En texto largo de 10 caracteres, el 50% es 5.
        res = service._fallback_embed("1234567890", failed_provider="gemini")
        
        assert res == [0.5, 0.6]
        # Debería haber truncado al 50% ("12345")
        mock_jina.assert_called_once_with(["12345"])
        assert service.provider == "jina"

@patch("app.services.embedding_service.logger")
def test_fallback_cascade_to_local(mock_logger):
    """Testea que si Jina falla, pasa a Local truncando el texto al 25%"""
    service = EmbeddingService(provider="jina")
    
    with patch.object(service, '_embed_local', return_value=[[0.9, 0.8]]) as mock_local:
        with patch.object(service, '_load_local_model', return_value=True):
            service._model = True # Mock
            # En texto de 12 caracteres, el 25% es 3.
            res = service._fallback_embed("123456789012", failed_provider="jina")
            
            assert res == [0.9, 0.8]
            # Debería haber truncado al 25% ("123")
            mock_local.assert_called_once_with(["123"])
            assert service.method == "local"
