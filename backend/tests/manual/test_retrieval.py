"""
test_retrieval.py

Prueba manual de la etapa de recuperación:
Vector Store ya indexado -> Denso + BM25 -> RRF -> Reranking (Jina/Cohere).

Reutiliza el mismo documento de prueba que test_vector_store.py
(sample_sections.md), para no duplicar datos de ejemplo.

Ejecución desde backend/:
uv run python tests/manual/test_retrieval.py
"""

import os
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.ingester_service import IngesterService
from app.services.vector_store_service import get_store, save_store, clear_store_cache
from app.services.retrieval_service import RetrievalService
from app.services.reranker_service import BaseReranker

SEPARATOR = "-" * 60
TEST_STORE_ROOT = Path(__file__).parent / "sample_vector_store"
TEST_DOCUMENT_ID = "test-doc-security-lists"


def cleanup_test_dir():
    if TEST_STORE_ROOT.exists():
        shutil.rmtree(TEST_STORE_ROOT)
    clear_store_cache()


def build_indexed_document() -> EmbeddingService:
    """Reproduce el mismo pipeline de ingesta+embeddings+índice que
    test_vector_store.py, dejando TEST_DOCUMENT_ID listo para recuperar."""
    sample_file = Path(__file__).parent / "sample_docs" / "sample_sections.md"
    ingester = IngesterService()
    document = ingester.process_document(sample_file, title="Documentación OCI Redes")
    rag_payload = ingester.build_rag_chunks(document)

    embedding_svc = EmbeddingService()
    child_texts = [c["content"] for c in rag_payload["child_chunks"]]
    embeddings = embedding_svc.embed_batch(child_texts)

    vector_store = get_store(TEST_DOCUMENT_ID)
    vector_store.add_documents(
        child_chunks=rag_payload["child_chunks"],
        embeddings=embeddings,
        parent_chunks=rag_payload["parent_chunks"],
        model_name=embedding_svc.model_name,
    )
    save_store(TEST_DOCUMENT_ID, vector_store)
    return embedding_svc


def test_end_to_end_retrieval(embedding_svc: EmbeddingService):
    print("\n" + SEPARATOR)
    print("PASO 1: Recuperación de extremo a extremo (denso + BM25 + RRF + rerank)")
    print(SEPARATOR)

    retrieval_svc = RetrievalService(embedding_service=embedding_svc)
    query = "firewall virtual y filtrado de tráfico"
    print(f"  Consulta: '{query}'")

    results = retrieval_svc.retrieve(document_id=TEST_DOCUMENT_ID, query=query, top_k=2)

    assert len(results) > 0, "La recuperación no debería devolver una lista vacía"
    for idx, parent in enumerate(results):
        score = parent.get("relevance_score")
        print(f"    [{idx+1}] ID: {parent['id']} | Título: {parent['title']} | Score: {score}")

    assert "Security Lists" in results[0]["title"] or "Security" in results[0]["content"], (
        "Se esperaba que 'Security Lists' quedara primero para esta consulta"
    )
    print("  ✅ Recuperación de extremo a extremo OK")


def test_empty_document_returns_empty_list(embedding_svc: EmbeddingService):
    print("\n" + SEPARATOR)
    print("PASO 2: Documento sin indexar devuelve lista vacía (sin lanzar error)")
    print(SEPARATOR)

    retrieval_svc = RetrievalService(embedding_service=embedding_svc)
    results = retrieval_svc.retrieve(document_id="documento-inexistente-xyz", query="algo", top_k=3)

    assert results == [], "Un documento sin índice debe devolver una lista vacía, no lanzar una excepción"
    print("  ✅ Manejo de documento vacío OK")


# ---------------------------------------------------------------------------
# Rerankers de prueba (inventados a propósito, solo para forzar cada rama
# de la cadena de fallback sin depender de las API reales de Jina/Cohere).
# ---------------------------------------------------------------------------
class _AlwaysFailsReranker(BaseReranker):
    def rerank(self, query, documents, top_n):
        raise RuntimeError("Fallo simulado: proveedor caído")


class _WorksReranker(BaseReranker):
    """Devuelve los documentos en orden inverso, para que el resultado sea
    inequívocamente distinto del orden RRF original."""
    def rerank(self, query, documents, top_n):
        reversed_indices = list(range(len(documents) - 1, -1, -1))[:top_n]
        return [{"index": i, "relevance_score": 1.0} for i in reversed_indices]


def test_reranker_fallback_chain(embedding_svc: EmbeddingService):
    print("\n" + SEPARATOR)
    print("PASO 3: Cadena de fallback del reranker (Jina -> Cohere -> orden RRF)")
    print(SEPARATOR)

    candidates = [
        {"id": "p0", "title": "Uno", "content": "contenido uno"},
        {"id": "p1", "title": "Dos", "content": "contenido dos"},
    ]

    retrieval_svc = RetrievalService(embedding_service=embedding_svc)

    # Caso A: el primer proveedor falla, el segundo responde -> se usa el segundo.
    retrieval_svc._rerankers = [_AlwaysFailsReranker(), _WorksReranker()]
    result_a = retrieval_svc._rerank("consulta de prueba", candidates, top_k=2)
    print(f"  Caso A (falla el primero): orden resultante = {[r['id'] for r in result_a]}")
    assert [r["id"] for r in result_a] == ["p1", "p0"], "Debió usarse _WorksReranker (orden invertido)"
    print("  ✅ Fallback al segundo proveedor OK")

    # Caso B: ambos fallan -> se conserva el orden RRF original, sin lanzar excepción.
    retrieval_svc._rerankers = [_AlwaysFailsReranker(), _AlwaysFailsReranker()]
    result_b = retrieval_svc._rerank("consulta de prueba", candidates, top_k=2)
    print(f"  Caso B (fallan ambos): orden resultante = {[r['id'] for r in result_b]}")
    assert [r["id"] for r in result_b] == ["p0", "p1"], "Debió conservarse el orden RRF original"
    print("  ✅ Fallback final a orden RRF OK")


if __name__ == "__main__":
    print("=" * 60)
    print("NuevaMente — Test Manual: RetrievalService")
    print("=" * 60)

    cleanup_test_dir()
    original_store_dir = settings.VECTOR_STORE_DIR
    settings.VECTOR_STORE_DIR = str(TEST_STORE_ROOT)

    try:
        embedding_svc = build_indexed_document()
        test_end_to_end_retrieval(embedding_svc)
        test_empty_document_returns_empty_list(embedding_svc)
        test_reranker_fallback_chain(embedding_svc)
    finally:
        settings.VECTOR_STORE_DIR = original_store_dir
        cleanup_test_dir()

    print("\n" + "=" * 60)
    print("¡Todos los tests de Retrieval pasaron exitosamente!")
    print("=" * 60)