"""
test_vector_store.py

Prueba manual de la cadena completa:
Ingesta -> Chunking (Parent-Child) -> Embeddings -> Vector Store (FAISS),
usando la fábrica por documento (get_store / save_store) en vez de
instanciar FAISSVectorStore directamente.

Ejecución desde backend/:
uv run python tests/manual/test_vector_store.py
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
from app.services import vector_store_service
from app.services.vector_store_service import (
    FAISSVectorStore,
    IncompatibleEmbeddingModelError,
    get_store,
    save_store,
    clear_store_cache,
)

SEPARATOR = "-" * 60
TEST_STORE_ROOT = Path(__file__).parent / "sample_vector_store"
TEST_DOCUMENT_ID = "test-doc-security-lists"


def cleanup_test_dir():
    if TEST_STORE_ROOT.exists():
        shutil.rmtree(TEST_STORE_ROOT)
    clear_store_cache()


def run_full_pipeline_test():
    print("=" * 60)
    print("NuevaMente — Test Manual: FAISS Vector Store Pipeline")
    print("=" * 60)

    cleanup_test_dir()
    # Redirige el directorio de índices a una carpeta de prueba aislada,
    # para no tocar vector_store/ real. Se restaura al final del test.
    original_store_dir = settings.VECTOR_STORE_DIR
    settings.VECTOR_STORE_DIR = str(TEST_STORE_ROOT)

    try:
        # Step 1: Ingestion and Parent-Child chunking
        print("\n" + SEPARATOR)
        print("PASO 1: Ingesta y Fragmentación Jerárquica")
        print(SEPARATOR)
        sample_file = Path(__file__).parent / "sample_docs" / "sample_sections.md"
        ingester = IngesterService()
        document = ingester.process_document(sample_file, title="Documentación OCI Redes")
        rag_payload = ingester.build_rag_chunks(document)

        parent_chunks = rag_payload["parent_chunks"]
        child_chunks = rag_payload["child_chunks"]

        print(f"  Documento procesado : {document.title}")
        print(f"  Parent Chunks creados: {len(parent_chunks)}")
        print(f"  Child Chunks creados : {len(child_chunks)}")
        assert len(parent_chunks) > 0 and len(child_chunks) > 0
        print("  ✅ Ingesta y Chunking OK")

        # Step 2: Embedding Generation
        print("\n" + SEPARATOR)
        print("PASO 2: Generación de Embeddings para Child Chunks")
        print(SEPARATOR)
        embedding_svc = EmbeddingService()
        print(f"  Proveedor activo : {embedding_svc.provider}")
        print(f"  Modelo activo    : {embedding_svc.model_name}")

        child_texts = [c["content"] for c in child_chunks]
        embeddings = embedding_svc.embed_batch(child_texts)

        dim = len(embeddings[0])
        print(f"  Vectores generados: {len(embeddings)} | Dimensión: {dim}")
        assert dim == settings.EMBEDDING_DIMENSIONS, (
            f"Se esperaban {settings.EMBEDDING_DIMENSIONS} dimensiones, llegaron {dim}"
        )
        print("  ✅ Generación de Embeddings OK")

        # Step 3: Vector Store Indexing via the per-document factory
        print("\n" + SEPARATOR)
        print("PASO 3: Indexación en FAISS vía get_store(document_id)")
        print(SEPARATOR)
        vector_store = get_store(TEST_DOCUMENT_ID)
        vector_store.add_documents(
            child_chunks=child_chunks,
            embeddings=embeddings,
            parent_chunks=parent_chunks,
            model_name=embedding_svc.model_name,
        )
        save_store(TEST_DOCUMENT_ID, vector_store)
        print(f"  Dimensión asignada al store tras indexar: {vector_store.dimension}")
        print(f"  Model name registrado: {vector_store.model_name}")
        print(f"  Total vectores en índice FAISS: {vector_store.index.ntotal}")
        assert vector_store.dimension == settings.EMBEDDING_DIMENSIONS
        assert vector_store.model_name == embedding_svc.model_name, (
            "model_name debe quedar asignado tras el primer add_documents() — "
            "si esto falla, get_store() está pre-inicializando el índice de nuevo"
        )
        assert vector_store.index.ntotal == len(child_chunks)
        print("  ✅ Indexación en FAISS OK")

        # Step 3b: In-process cache reuses the same instance
        print("\n" + SEPARATOR)
        print("PASO 3b: Verificación del caché en memoria de get_store()")
        print(SEPARATOR)
        same_store = get_store(TEST_DOCUMENT_ID)
        print(f"  ¿Misma instancia devuelta por el caché?: {same_store is vector_store}")
        assert same_store is vector_store, "get_store() debe reutilizar la instancia cacheada"
        print("  ✅ Caché en memoria OK")

        # Step 4: Semantic Search & Parent Document Resolution
        print("\n" + SEPARATOR)
        print("PASO 4: Búsqueda Semántica y Resolución de Padres")
        print(SEPARATOR)
        query = "firewall virtual y filtrado de tráfico"
        print(f"  Consulta: '{query}'")

        query_vector = embedding_svc.embed_text(query, is_query=True)

        # 4.1 Search child chunks
        child_results = vector_store.similarity_search(
            query_embedding=query_vector,
            query_model_name=embedding_svc.model_name,
            top_k=2,
        )
        print("  Hijos más relevantes encontrados:")
        for idx, c in enumerate(child_results):
            print(f"    [{idx+1}] Score: {c['score']:.4f} | Parent: {c['parent_id']} | Breadcrumb: {c['breadcrumb']}")

        # 4.2 Retrieve parent documents
        parent_results = vector_store.retrieve_parent_chunks(
            query_embedding=query_vector,
            query_model_name=embedding_svc.model_name,
            top_k_parents=1,
        )
        print("  Padres recuperados para contexto del LLM:")
        for idx, p in enumerate(parent_results):
            print(f"    [{idx+1}] ID: {p['id']} | Título: {p['title']} | Relevance Score: {p['relevance_score']:.4f}")
            print(f"        Contenido: {p['content'][:120]}...")

        assert len(parent_results) > 0
        # Expected best match for firewall query is Security Lists
        assert "Security Lists" in parent_results[0]["title"] or "Security" in parent_results[0]["content"]
        print("  ✅ Búsqueda Semántica y Recuperación de Padres OK")

        # Step 5: Persistence (Save & Load, via the factory)
        print("\n" + SEPARATOR)
        print("PASO 5: Persistencia (Guardar y Recargar desde Disco)")
        print(SEPARATOR)
        store_dir = TEST_STORE_ROOT / TEST_DOCUMENT_ID
        print(f"  Índice guardado en: {store_dir}")
        assert (store_dir / "index.faiss").exists()
        assert (store_dir / "metadata.json").exists()

        # Clear the in-process cache to force a real reload from disk.
        clear_store_cache(TEST_DOCUMENT_ID)
        reloaded_store = get_store(TEST_DOCUMENT_ID)
        print(f"  Índice recargado con éxito. Total vectores: {reloaded_store.index.ntotal}")
        assert reloaded_store.index.ntotal == vector_store.index.ntotal
        assert reloaded_store is not vector_store, "Tras limpiar el caché debe crearse una instancia nueva"

        # Verify search still works on the reloaded index
        reloaded_search = reloaded_store.similarity_search(
            query_embedding=query_vector,
            query_model_name=reloaded_store.model_name,
            top_k=1,
        )
        print(f"  Búsqueda post-recarga score: {reloaded_search[0]['score']:.4f}")
        assert len(reloaded_search) == 1
        print("  ✅ Persistencia en Disco OK")

        # Step 6: Model Incompatibility Protection
        print("\n" + SEPARATOR)
        print("PASO 6: Protección de Incompatibilidad entre Modelos")
        print(SEPARATOR)
        incompatible_model = "modelo-incompatible-v999"
        try:
            reloaded_store.similarity_search(
                query_embedding=query_vector,
                query_model_name=incompatible_model,
            )
            print("  ❌ ERROR: No debió permitir la búsqueda con modelo incompatible.")
            assert False
        except IncompatibleEmbeddingModelError as err:
            print(f"  Capturada excepción esperada: {err}")
            print("  ✅ Bloqueo por modelo incompatible OK")

    finally:
        settings.VECTOR_STORE_DIR = original_store_dir
        cleanup_test_dir()

    print("\n" + "=" * 60)
    print("¡Todos los tests del Vector Store pasaron exitosamente!")
    print("=" * 60)


if __name__ == "__main__":
    run_full_pipeline_test()