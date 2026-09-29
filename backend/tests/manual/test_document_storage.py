"""
test_document_storage.py

Prueba manual de almacenamiento de documentos sobre Supabase:
document_storage_service.py (archivo original en el bucket) +
document_repository.py (metadata y estado en la tabla `documents`).

Requiere SUPABASE_URL y SUPABASE_KEY en backend/.env, el bucket
"document-source" ya creado, y la tabla `documents` ya migrada
(migrations/001_documents.sql). Si algo de esto falta, el script lo
reporta y se detiene sin marcar el resto como fallido.

Ejecución desde backend/:
uv run python tests/manual/test_document_storage.py
"""

import os
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings
from app.infrastructure.supabase_client import get_supabase_client
from app.services.document_storage_service import get_document_storage
from app.services.document_repository import get_document_repository
from app.schemas.document_record import STATUS_PROCESSING, STATUS_READY, STATUS_FAILED

SEPARATOR = "-" * 60
SAMPLE_FILE = Path(__file__).parent / "sample_docs" / "sample_vcn.txt"

# document_id debe ser un UUID válido: la columna en Postgres es de tipo
# `uuid`, y un prefijo de texto (como "test-") rompe su parseo estricto.
TEST_DOCUMENT_ID = str(uuid.uuid4())


def check_prerequisites() -> bool:
    print("=" * 60)
    print("NuevaMente — Test Manual: Document Storage (Supabase)")
    print("=" * 60)

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("  ⏭️  SUPABASE_URL / SUPABASE_KEY no configuradas — omitiendo test completo.")
        return False
    if not SAMPLE_FILE.exists():
        print(f"  ⏭️  No se encontró {SAMPLE_FILE} — omitiendo test completo.")
        return False

    print(f"  Bucket configurado: {settings.SUPABASE_BUCKET_DOCUMENTS}")
    print(f"  Documento de prueba: {TEST_DOCUMENT_ID}")
    return True


def test_upload_and_download_roundtrip():
    print("\n" + SEPARATOR)
    print("PASO 1: Subir y descargar el archivo original")
    print(SEPARATOR)

    storage = get_document_storage()
    object_key = storage.upload_document(
        local_path=str(SAMPLE_FILE),
        user_id=None,
        document_id=TEST_DOCUMENT_ID,
    )
    print(f"  object_key generado: {object_key}")
    assert object_key.endswith(SAMPLE_FILE.suffix), "El object_key debería conservar la extensión original"
    assert TEST_DOCUMENT_ID in object_key

    destination = Path(__file__).parent / "sample_vector_store" / f"downloaded_{SAMPLE_FILE.name}"
    downloaded_path = storage.download_document(object_key, str(destination))
    print(f"  Descargado en: {downloaded_path}")

    original_bytes = SAMPLE_FILE.read_bytes()
    downloaded_bytes = Path(downloaded_path).read_bytes()
    assert original_bytes == downloaded_bytes, "El contenido descargado debe ser idéntico al original"
    destination.unlink()  # limpia el archivo local descargado, no el remoto
    print("  ✅ Subida y descarga OK — contenido idéntico")

    return object_key


def test_document_status_lifecycle(object_key: str):
    print("\n" + SEPARATOR)
    print("PASO 2: Ciclo de estado en la tabla documents")
    print(SEPARATOR)

    repo = get_document_repository()

    # 2.1 Creación -> processing
    record = repo.create_document(
        document_id=TEST_DOCUMENT_ID,
        title="Documento de prueba (VCN)",
        source_filename=SAMPLE_FILE.name,
        object_key=object_key,
        user_id=None,
    )
    print(f"  Creado con status: {record.status}")
    assert record.status == STATUS_PROCESSING
    print("  ✅ Creación en estado 'processing' OK")

    # 2.2 mark_ready -> ready
    repo.mark_ready(TEST_DOCUMENT_ID, total_parents=3, total_children=9)
    fetched = repo.get_document(TEST_DOCUMENT_ID)
    print(f"  Tras mark_ready: status={fetched.status}, parents={fetched.total_parents}, children={fetched.total_children}")
    assert fetched.status == STATUS_READY
    assert fetched.total_parents == 3 and fetched.total_children == 9
    print("  ✅ Transición a 'ready' OK")

    # 2.3 mark_failed -> failed (se prueba sobre el mismo doc para no crear
    # datos de prueba adicionales; en la práctica un documento no pasaría
    # por ambas transiciones en una sola ejecución real).
    repo.mark_failed(TEST_DOCUMENT_ID, error_message="Fallo simulado para la prueba")
    fetched = repo.get_document(TEST_DOCUMENT_ID)
    print(f"  Tras mark_failed: status={fetched.status}, error={fetched.error_message}")
    assert fetched.status == STATUS_FAILED
    assert fetched.error_message == "Fallo simulado para la prueba"
    print("  ✅ Transición a 'failed' OK")

    # 2.4 get_document sobre un UUID válido pero inexistente -> None, sin
    # lanzar excepción.
    missing = repo.get_document(str(uuid.uuid4()))
    assert missing is None
    print("  ✅ get_document() de un UUID inexistente devuelve None OK")

    # 2.5 get_document con un ID mal formado -> mensaje claro (ValueError),
    # no el error interno de Postgrest.
    try:
        repo.get_document("documento-que-no-existe-nunca")
        print("  ❌ ERROR: debió rechazar un document_id que no es un UUID válido.")
        assert False
    except ValueError as err:
        print(f"  Mensaje claro recibido: {err}")
        print("  ✅ Validación de formato de UUID OK — sin traza interna de Postgrest")
    assert missing is None
    print("  ✅ get_document() de un UUID inexistente devuelve None OK")


def test_list_documents_includes_test_record():
    print("\n" + SEPARATOR)
    print("PASO 3: Listado de documentos")
    print(SEPARATOR)

    repo = get_document_repository()
    all_documents = repo.list_documents()  # sin login: sin filtro, devuelve todos
    ids = [doc.document_id for doc in all_documents]
    print(f"  Total de documentos en la tabla: {len(all_documents)}")
    assert TEST_DOCUMENT_ID in ids, "El documento de prueba debería aparecer en el listado"
    print("  ✅ El documento de prueba aparece en list_documents() OK")


def cleanup(object_key: str):
    """Borra el objeto del bucket y la fila de prueba, pero solo tras
    confirmación manual — útil mientras se verifica por primera vez que la
    subida a Supabase realmente funciona, antes de confiar en el borrado
    automático. Usa el cliente de Supabase directamente porque borrar no es
    parte de la interfaz pública de BaseDocumentStorage/BaseDocumentRepository
    — es solo higiene del test."""
    print("\n" + SEPARATOR)
    print("LIMPIEZA: datos de prueba creados")
    print(SEPARATOR)
    print(f"  Objeto en el bucket : {settings.SUPABASE_BUCKET_DOCUMENTS}/{object_key}")
    print(f"  Fila en la tabla    : documents.document_id = {TEST_DOCUMENT_ID}")
    print("  Puedes verificarlos ahora mismo en el dashboard de Supabase.")

    answer = input("\n  ¿Eliminar estos datos de prueba? [s/N]: ").strip().lower()
    if answer != "s":
        print("  ⏭️  Limpieza omitida — los datos de prueba quedan en Supabase.")
        return

    client = get_supabase_client()
    try:
        client.storage.from_(settings.SUPABASE_BUCKET_DOCUMENTS).remove([object_key])
        print(f"  Objeto eliminado del bucket: {object_key}")
    except Exception as exc:
        print(f"  ⚠️  No se pudo eliminar el objeto del bucket: {exc}")

    try:
        client.table("documents").delete().eq("document_id", TEST_DOCUMENT_ID).execute()
        print(f"  Fila eliminada de la tabla documents: {TEST_DOCUMENT_ID}")
    except Exception as exc:
        print(f"  ⚠️  No se pudo eliminar la fila de la tabla: {exc}")


if __name__ == "__main__":
    if not check_prerequisites():
        sys.exit(0)

    object_key = None
    try:
        object_key = test_upload_and_download_roundtrip()
        test_document_status_lifecycle(object_key)
        test_list_documents_includes_test_record()

        print("\n" + "=" * 60)
        print("¡Todos los tests de Document Storage pasaron exitosamente!")
        print("=" * 60)
    finally:
        if object_key:
            cleanup(object_key)