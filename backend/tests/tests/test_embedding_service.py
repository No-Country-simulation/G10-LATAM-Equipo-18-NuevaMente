"""
test_embedding_service.py

Purpose:
    Unit tests for EmbeddingService covering successful single/batch embeddings,
    rate-limit token threshold proactive routing, and cascade fallback
    across Gemini -> Jina -> local models.

Input:
    Sample string texts and mock provider responses.

Output:
    Test assertions verifying provider dispatch, fallback transitions, and vector formatting.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.services.embedding_service import EmbeddingService, estimate_tokens


def _dummy_vector(dim: int = 768, val: float = 0.5):
    """Produces a dummy vector of the specified dimension."""
    vec = [0.0] * dim
    vec[0] = val
    return vec


def test_estimate_tokens():
    texts = ["1234", "12345678"]
    # 4 chars -> 1 token, 8 chars -> 2 tokens. Total = 3
    assert estimate_tokens(texts) == 3


def test_embed_text_gemini_success():
    service = EmbeddingService(provider="gemini")
    dummy = _dummy_vector(service.dimensions, 1.0)

    with patch.object(service, "_embed_gemini_in_batches", return_value=[dummy]) as mock_gemini:
        res = service.embed_text("Sample query", is_query=False)
        assert len(res) == service.dimensions
        mock_gemini.assert_called_once()


def test_fallback_cascade_from_gemini_to_jina():
    service = EmbeddingService(provider="gemini")
    dummy = _dummy_vector(service.dimensions, 1.0)

    with patch.object(service, "_embed_gemini_in_batches", side_effect=RuntimeError("Gemini 429")):
        with patch.object(service, "_embed_jina_in_batches", return_value=[dummy]) as mock_jina:
            res = service.embed_batch(["Sample text"])
            assert len(res) == 1
            mock_jina.assert_called_once()
            assert service.provider == "jina"
            assert "jina" in service.model_name


def test_fallback_cascade_to_local_when_remote_providers_fail():
    service = EmbeddingService(provider="gemini")
    dummy = _dummy_vector(service.dimensions, 1.0)

    with patch.object(service, "_embed_gemini_in_batches", side_effect=RuntimeError("Gemini 429")):
        with patch.object(service, "_embed_jina_in_batches", side_effect=RuntimeError("Jina down")):
            with patch.object(service, "_embed_local", return_value=[dummy]) as mock_local:
                res = service.embed_batch(["Sample text"])
                assert len(res) == 1
                mock_local.assert_called_once()
                assert service.provider == "local"
                assert service.method == "local"


def test_proactive_routing_when_tokens_exceed_gemini_safe_limit():
    service = EmbeddingService(provider="gemini")
    # Generate texts exceeding GEMINI_SAFE_TPM (25,000 tokens ≈ 100,000 chars)
    large_text = "a" * (settings.GEMINI_SAFE_TPM * 4 + 100)
    texts = [large_text]

    dummy = _dummy_vector(service.dimensions, 1.0)
    with patch.object(service, "_embed_gemini_in_batches") as mock_gemini:
        with patch.object(service, "_embed_jina_in_batches", return_value=[dummy]) as mock_jina:
            res = service.embed_batch(texts)
            assert len(res) == 1
            # Gemini should have been bypassed pro-actively
            mock_gemini.assert_not_called()
            mock_jina.assert_called_once()
            assert service.provider == "jina"
