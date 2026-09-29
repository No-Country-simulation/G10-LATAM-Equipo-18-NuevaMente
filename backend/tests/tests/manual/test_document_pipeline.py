"""
test_document_pipeline.py

Prueba manual del orquestador de extremo a extremo:
Subida a Supabase Storage -> fila en documents -> ingesta -> embeddings ->
indexación en FAISS.

Reutiliza el mismo documento de prueba que test_vector_store.py y
test_retrieval.py (sample_sections.md), y requiere lo mismo que
test_document_storage.py: SUPABASE_URL/KEY configuradas, el bucket
"document-source" y la tabla "documents" ya creados.

Ejecución desde backend/:
uv run python tests/manual/test_document_pipeline.py
"""

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings
from app.infrastructure.supabase_client import get_supabase_client
from app.schemas.document_record import STATUS_READY, STATUS_FAILED
from app.services.vector_store_service import clear_store_cache
from app.services import document_pipeline_service
from app.services.document_pipeline_service import process_and_index_document

SEPARATOR = "-" * 60
SAMPLE_FILE = Path(__file__).parent / "sample_docs" / "sample_sections.md"
TEST_STORE_ROOT = Path(__file__).parent / "sample_vector_store"


def check_prerequisites() -> bool:
    print("=" * 60)
    print("NuevaMente — Test Manual: Document Pipeline (extremo a extremo)")
    print("=" * 60)

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("  ⏭️  SUPABASE_URL / SUPABASE_KEY no configuradas — omitiendo test completo.")
        return False
    if not SAMPLE_FILE.exists():
        print(f"  ⏭️  No se encontró {SAMPLE_FILE} — omitiendo test completo.")
        return False
    return True


def cleanup(document_id: str, object_key: str):
    """Higiene del test: borra el objeto del bucket, la fila de la tabla, y
    el índice local, preguntando confirmación igual que test_document_storage.py."""
    print("\n" + SEPARATOR)
    print("LIMPIEZA: datos de prueba creados")
    print(SEPARATOR)
    print(f"  document_id         : {document_id}")
    print(f"  Objeto en el bucket  : {settings.SUPABASE_BUCKET_DOCUMENTS}/{object_key}")
    print(f"  Índice local en      : {TEST_STORE_ROOT / document_id}")

    answer = input("\n  ¿Eliminar estos datos de prueba? [s/N]: ").strip().lower()
    if answer != "s":
        print("  ⏭️  Limpieza omitida — los datos de prueba quedan como están.")
        return

    client = get_supabase_client()
    try:
        client.storage.from_(settings.SUPABASE_BUCKET_DOCUMENTS).remove([object_key])
        print(f"  Objeto eliminado del bucket: {object_key}")
    except Exception as exc:
        print(f"  ⚠️  No se pudo eliminar el objeto del bucket: {exc}")

    try:
        client.table("documents").delete().eq("document_id", document_id).execute()
        print(f"  Fila eliminada de la tabla documents: {document_id}")
    except Exception as exc:
        print(f"  ⚠️  No se pudo eliminar la fila de la tabla: {exc}")

    clear_store_cache(document_id)
    if (TEST_STORE_ROOT / document_id).exists():
        shutil.rmtree(TEST_STORE_ROOT / document_id)
        print(f"  Índice local eliminado: {TEST_STORE_ROOT / document_id}")


def test_pipeline_success():
    print("\n" + SEPARATOR)
    print("PASO 1: Pipeline completo con un documento válido")
    print(SEPARATOR)

    record = process_and_index_document(local_path=str(SAMPLE_FILE), title="Documentación OCI Redes")

    print(f"  document_id      : {record.document_id}")
    print(f"  status           : {record.status}")
    print(f"  object_key       : {record.object_key}")
    print(f"  total_parents    : {record.total_parents}")
    print(f"  total_children   : {record.total_children}")

    assert record.status == STATUS_READY, f"Se esperaba status='ready', llegó '{record.status}'"
    assert record.total_parents and record.total_parents > 0
    assert record.total_children and record.total_children > 0
    print("  ✅ Pipeline completo terminó en 'ready' OK")

    return record


def test_pipeline_marks_failed_on_embedding_error():
    print("\n" + SEPARATOR)
    print("PASO 2: Fallo a mitad de camino queda registrado como 'failed'")
    print(SEPARATOR)
    print("  Simula un fallo en la generación de embeddings (sin llamar a la")
    print("  API real) y verifica que el documento no quede atascado en")
    print("  'processing', sino marcado explícitamente como 'failed'.")

    from app.services.document_repository import get_document_repository

    def failing_ingest_embed_and_index(path, title, document_id, repo, on_progress=None):
        raise RuntimeError("Fallo simulado de embeddings")

    # Eventos de progreso recibidos por el callback durante esta ejecución.
    eventos = []

    with patch.object(
        document_pipeline_service, "_ingest_embed_and_index", side_effect=failing_ingest_embed_and_index
    ):
        try:
            process_and_index_document(
                local_path=str(SAMPLE_FILE),
                title="Documento que fallará",
                on_progress=eventos.append,
            )
            print("  ❌ ERROR: debió propagar la excepción simulada.")
            assert False
        except RuntimeError as err:
            print(f"  Excepción propagada como se esperaba: {err}")

    # No tenemos el document_id generado internamente (process_and_index_document
    # no lo expone si falla), así que buscamos el registro más reciente en estado
    # 'failed' con el título usado en esta prueba.
    repo = get_document_repository()
    recent_failed = [d for d in repo.list_documents() if d.title == "Documento que fallará"]
    assert recent_failed, "No se encontró el documento fallido en la tabla"
    failed_record = recent_failed[-1]

    etapas = [evento["stage"] for evento in eventos]
    print(f"  Etapas de progreso reportadas: {etapas}")
    assert etapas == ["uploading", "failed"], f"Etapas inesperadas: {etapas}"

    print(f"  document_id: {failed_record.document_id} | status: {failed_record.status}")
    print(f"  error_message: {failed_record.error_message}")
    assert failed_record.status == STATUS_FAILED
    assert "Fallo simulado" in failed_record.error_message
    print("  ✅ Documento quedó correctamente marcado como 'failed' OK")

    return failed_record


if __name__ == "__main__":
    if not check_prerequisites():
        sys.exit(0)

    success_record = None
    failed_record = None
    try:
        success_record = test_pipeline_success()
        failed_record = test_pipeline_marks_failed_on_embedding_error()

        print("\n" + "=" * 60)
        print("¡Todos los tests del Document Pipeline pasaron exitosamente!")
        print("=" * 60)
    finally:
        if success_record:
            cleanup(success_record.document_id, success_record.object_key)
        if failed_record:
            cleanup(failed_record.document_id, failed_record.object_key)