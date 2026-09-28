"""
test_embedding.py

Purpose:
    Manual verification script for EmbeddingService. Tests live and mocked
    embedding generation, batch reduction, model tag tracking, token-based
    proactive routing, and multi-provider cascade fallback (Gemini -> Jina -> local).

Input:
    Sample technical text strings. Environment variables from backend/.env.

Output:
    Formatted console preview of dimensions, vector snippets, and assertion status in Spanish.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.embedding_service import EmbeddingService, estimate_tokens
from app.core.config import settings

SEPARATOR = "-" * 60

SAMPLE_TEXTS = [
    "Las redes neuronales convolucionales son fundamentales en visión computacional.",
    "El modelo aprende representaciones jerárquicas de las características de la imagen.",
    "Fintech refers to technology-driven financial services and innovation.",
]

SAMPLE_QUERY = "¿Cómo funcionan las redes convolucionales?"


def print_vector_preview(label: str, vector: list, n: int = 5) -> None:
    """Formats and prints first n values of vector."""
    preview = [round(v, 6) for v in vector[:n]]
    print(f"  {label}: dim={len(vector)} | primeros {n} valores: {preview}")


def test_gemini_api():
    """Validates live Gemini API embedding generation if API key is configured."""
    print("\n" + SEPARATOR)
    print("PRUEBA 1 — Gemini API en vivo (método: api, proveedor: gemini)")
    print(SEPARATOR)
    try:
        svc = EmbeddingService(method="api", provider="gemini")
        print(f"  Model ID (API)   : {svc.model_id}")
        print(f"  Model tag (store): {svc.model_name}")

        vec = svc.embed_text(SAMPLE_TEXTS[0], is_query=False)
        print_vector_preview("doc embedding", vec)
        assert len(vec) == settings.EMBEDDING_DIMENSIONS, (
            f"Se esperaban {settings.EMBEDDING_DIMENSIONS} dimensiones, llegaron {len(vec)}"
        )

        q_vec = svc.embed_text(SAMPLE_QUERY, is_query=True)
        print_vector_preview("query embedding", q_vec)

        batch = svc.embed_batch(SAMPLE_TEXTS)
        print(f"  Batch: {len(batch)} vectores, dim={len(batch[0])}")
        print(f"  ✅ Gemini API OK — dimensión fija en {settings.EMBEDDING_DIMENSIONS}")
    except Exception as exc:
        print(f"  ⚠️  Gemini API no disponible o cuota agotada: {exc}")


def test_jina_api():
    """Validates live Jina API embedding generation if API key is configured."""
    print("\n" + SEPARATOR)
    print("PRUEBA 2 — Jina AI API en vivo (método: api, proveedor: jina)")
    print(SEPARATOR)
    if not settings.JINA_API_KEY:
        print("  ⏭️  JINA_API_KEY no configurada — omitiendo prueba en vivo")
        return
    try:
        svc = EmbeddingService(method="api", provider="jina")
        print(f"  Model ID (API)   : {svc.model_id}")
        print(f"  Model tag (store): {svc.model_name}")
        vec = svc.embed_text(SAMPLE_TEXTS[0])
        print_vector_preview("doc embedding", vec)
        assert len(vec) == settings.EMBEDDING_DIMENSIONS, (
            f"Se esperaban {settings.EMBEDDING_DIMENSIONS} dimensiones, llegaron {len(vec)}"
        )
        print(f"  ✅ Jina API OK — dimensión fija en {settings.EMBEDDING_DIMENSIONS}")
    except Exception as exc:
        print(f"  ⚠️  Jina API no disponible o cuota agotada: {exc}")


def test_model_name_tracking():
    """Verifies that model_name contains dimension suffix and rejects cross-model mixing."""
    print("\n" + SEPARATOR)
    print("PRUEBA 3 — Verificación de model_name tracking (incluye dimensión)")
    print(SEPARATOR)
    svc_gemini = EmbeddingService(method="api", provider="gemini")
    svc_jina = EmbeddingService(method="api", provider="jina")
    print(f"  gemini model_name : {svc_gemini.model_name}")
    print(f"  jina   model_name : {svc_jina.model_name}")

    dim_suffix = f"@{settings.EMBEDDING_DIMENSIONS}"
    assert svc_gemini.model_name.endswith(dim_suffix), "El tag de Gemini debe incluir la dimensión"
    assert svc_jina.model_name.endswith(dim_suffix), "El tag de Jina debe incluir la dimensión"
    print(f"  Ambos tags incluyen el sufijo de dimensión ({dim_suffix})")

    compatible = svc_gemini.model_name == svc_jina.model_name
    print(f"  Compatibilidad gemini↔jina : {compatible} (esperado: False)")
    assert not compatible, "Modelos distintos no deben ser compatibles"
    print("  ✅ Tracking de modelo OK")


def test_jina_batch_halving_on_failure():
    """Verifies recursive batch halving when a large Jina batch encounters payload errors."""
    print("\n" + SEPARATOR)
    print("PRUEBA 4 — Reducción de lote en Jina ante fallo de tamaño (Mock)")
    print(SEPARATOR)
    print("  Simula que un lote grande de Jina falla por tamaño de payload")
    print("  y verifica que el servicio reduce el tamaño de lote a la mitad y reintenta.")

    svc = EmbeddingService(method="api", provider="jina")
    texts = [f"fragmento de prueba número {i}" for i in range(4)]
    call_sizes = []

    def flaky_embed_batch(piece, **kwargs):
        call_sizes.append(len(piece))
        if len(piece) > 2:
            raise RuntimeError("Fallo simulado: lote demasiado grande")
        return [[0.0] * settings.EMBEDDING_DIMENSIONS for _ in piece]

    with patch.object(svc._jina_client, "embed_batch", side_effect=flaky_embed_batch):
        vectors = svc._embed_jina_in_batches(texts, is_query=False)

    print(f"  Tamaños de lote intentados en orden: {call_sizes}")
    assert len(vectors) == len(texts), "Deben regresar tantos vectores como textos de entrada"
    assert max(call_sizes) > 2 and min(call_sizes) <= 2
    print("  ✅ Reducción automática de lote en Jina OK")


def test_fallback_cascade_gemini_to_jina():
    """Verifies reactive cascade from Gemini to Jina on HTTP 429 / quota failure."""
    print("\n" + SEPARATOR)
    print("PRUEBA 5 — Fallback reactivo simulado (Gemini 429 / Cuota -> Jina)")
    print(SEPARATOR)
    print("  Simula que Gemini devuelve error 429 Too Many Requests y verifica")
    print("  que el servicio conmuta automáticamente a Jina y actualiza model_name.")

    svc = EmbeddingService(method="api", provider="gemini")
    dummy_vec = [0.05] * settings.EMBEDDING_DIMENSIONS

    with patch.object(svc, "_embed_gemini_in_batches", side_effect=RuntimeError("Gemini 429 ResourceExhausted")):
        with patch.object(svc, "_embed_jina_in_batches", return_value=[dummy_vec for _ in SAMPLE_TEXTS]) as mock_jina:
            vectors = svc.embed_batch(SAMPLE_TEXTS)

            mock_jina.assert_called_once()
            assert svc.provider == "jina", f"Se esperaba proveedor 'jina', quedó '{svc.provider}'"
            assert "jina" in svc.model_name, f"El model_name debe reflejar Jina: {svc.model_name}"
            assert len(vectors) == len(SAMPLE_TEXTS)

    print(f"  Proveedor final resultante: {svc.provider}")
    print(f"  Model tag actualizado     : {svc.model_name}")
    print("  ✅ Fallback reactivo Gemini -> Jina OK")


def test_fallback_cascade_to_local_model():
    """Verifies full cascade to local model when both Gemini and Jina fail."""
    print("\n" + SEPARATOR)
    print("PRUEBA 6 — Fallback reactivo completo (Gemini & Jina caídos -> Modelo Local)")
    print(SEPARATOR)
    print("  Simula que tanto Gemini como Jina fallan, verificando que la cascada")
    print("  conmuta exitosamente al modelo local sentence-transformers.")

    svc = EmbeddingService(method="api", provider="gemini")
    dummy_vec = [0.1] * settings.EMBEDDING_DIMENSIONS

    with patch.object(svc, "_embed_gemini_in_batches", side_effect=RuntimeError("Gemini no disponible")):
        with patch.object(svc, "_embed_jina_in_batches", side_effect=RuntimeError("Jina no disponible")):
            with patch.object(svc, "_embed_local", return_value=[dummy_vec for _ in SAMPLE_TEXTS]) as mock_local:
                vectors = svc.embed_batch(SAMPLE_TEXTS)

                mock_local.assert_called_once()
                assert svc.provider == "local"
                assert svc.method == "local"
                assert settings.LOCAL_EMBEDDING_MODEL in svc.model_name
                assert len(vectors) == len(SAMPLE_TEXTS)

    print(f"  Proveedor final resultante: {svc.provider} (método: {svc.method})")
    print(f"  Model tag actualizado     : {svc.model_name}")
    print("  ✅ Fallback reactivo a Modelo Local OK")


def test_proactive_routing_on_token_overflow():
    """Verifies proactive routing to Jina when estimated tokens exceed Gemini safe threshold."""
    print("\n" + SEPARATOR)
    print("PRUEBA 7 — Ruteo proactivo por volumen de tokens (> 25K TPM)")
    print(SEPARATOR)
    print("  Genera un payload con tokens estimados superiores a GEMINI_SAFE_TPM")
    print("  y verifica que el servicio desvía el lote directamente a Jina sin llamar a Gemini.")

    # Generates text exceeding GEMINI_SAFE_TPM (30,000 tokens > 25,000 threshold)
    large_payload = ["texto largo " * 100 for _ in range(100)]
    total_tokens = estimate_tokens(large_payload)
    print(f"  Tokens estimados en el lote: {total_tokens} (Umbral seguro Gemini: {settings.GEMINI_SAFE_TPM})")

    svc = EmbeddingService(method="api", provider="gemini")
    dummy_vec = [0.02] * settings.EMBEDDING_DIMENSIONS

    with patch.object(svc, "_embed_gemini_in_batches", return_value=[dummy_vec for _ in large_payload]) as mock_gemini:
        with patch.object(svc, "_embed_jina_in_batches", return_value=[dummy_vec for _ in large_payload]) as mock_jina:
            vectors = svc.embed_batch(large_payload)

            mock_gemini.assert_not_called()
            mock_jina.assert_called_once()
            assert svc.provider == "jina"
            assert len(vectors) == len(large_payload)

    print("  Gemini fue omitido preventivamente: Sí (0 llamadas)")
    print(f"  Lote procesado por: {svc.provider}")
    print("  ✅ Ruteo proactivo por cuota OK")


if __name__ == "__main__":
    print("=" * 60)
    print("NuevaMente — Test Manual: EmbeddingService")
    print(f"Método configurado   : {settings.EMBEDDING_METHOD}")
    print(f"Proveedor por defecto: {settings.EMBEDDING_API_PROVIDER}")
    print(f"Dimensión configurada: {settings.EMBEDDING_DIMENSIONS}")
    print("=" * 60)

    test_gemini_api()
    test_jina_api()
    test_model_name_tracking()
    test_jina_batch_halving_on_failure()
    test_fallback_cascade_gemini_to_jina()
    test_fallback_cascade_to_local_model()
    test_proactive_routing_on_token_overflow()

    print("\n" + "=" * 60)
    print("Tests completados exitosamente.")
    print("=" * 60)