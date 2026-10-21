"""
test_document_deletion.py

Pytest suite for the permanent deletion of an indexed document:
- The metadata row, the FAISS index directory and the in-process store cache
  entry are all removed by one call.
- The stored file is deleted with the row's own object_key, never with a
  freshly built key.
- A storage failure leaves the row intact so the user can retry.
- An index failure leaves the row intact.
- A document owned by someone else is reported as missing (404), never as
  forbidden.
- A document that is still being processed is refused (409).
- Anonymous callers are rejected (401).
- Deleting an already deleted document reports it as missing.

Every test runs against a temporary SQLite database, a temporary vector store
directory and a fake object storage, so no network call happens and the real
documents are never touched.
"""

import sqlite3
import types
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.security import create_access_token
from app.services import vector_store_service
from app.services.document_repository import SQLiteDocumentRepository
from app.services.document_storage_service import OCIStorageAdapter

client = TestClient(app)

OWNER_ID = "usr_ana_001"
OWNER_EMAIL = "ana.martinez@empresa.com"

OTHER_ID = "usr_diego_002"
OTHER_EMAIL = "diego.fuentes@empresa.com"

_AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    timestamp REAL NOT NULL
)
"""


class FakeStorage:
    """Object storage double that records the keys it was asked to delete."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.deleted_keys: list[str] = []

    def delete_document(self, object_key: str) -> None:
        if self.error is not None:
            raise self.error
        self.deleted_keys.append(object_key)


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Points the document repository and the audit log at a temporary db."""
    db_path = tmp_path / "deletion_test.db"

    def _get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr("app.services.document_repository.get_db", _get_db)
    monkeypatch.setattr("app.services.document_deletion_service.get_db", _get_db)

    conn = _get_db()
    try:
        conn.execute(_AUDIT_LOG_DDL)
        conn.commit()
    finally:
        conn.close()

    return db_path


@pytest.fixture
def repo(temp_db):
    """The SQLite document repository bound to the temporary database."""
    return SQLiteDocumentRepository()


@pytest.fixture
def vector_store_dir(monkeypatch, tmp_path):
    """Redirects the vector store to a temporary directory."""
    root = tmp_path / "vector_store"

    def _document_store_dir(document_id: str):
        return root / document_id

    monkeypatch.setattr(vector_store_service, "_document_store_dir", _document_store_dir)
    vector_store_service.clear_store_cache()
    yield root
    vector_store_service.clear_store_cache()


@pytest.fixture
def storage(monkeypatch):
    """Replaces the object storage backend with a recording double."""
    fake = FakeStorage()
    monkeypatch.setattr(
        "app.services.document_deletion_service.get_document_storage",
        lambda: fake,
    )
    return fake


@pytest.fixture
def auth_headers_owner():
    token = create_access_token(OWNER_ID, OWNER_EMAIL, "Ana Martinez", "Instructor")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_other():
    token = create_access_token(OTHER_ID, OTHER_EMAIL, "Diego Fuentes", "Lider Tecnico")
    return {"Authorization": f"Bearer {token}"}


def insert_document(
    repo,
    document_id: str,
    user_id: str = OWNER_ID,
    status: str = "ready",
    object_key: str | None = None,
) -> str:
    """Creates a document row and returns the object key it was stored with."""
    key = object_key or f"usuarios/{user_id}/documentos/{document_id}.pdf"
    repo.create_document(
        document_id=document_id,
        title="Manual de arquitectura VCN",
        source_filename="manual_vcn.pdf",
        object_key=key,
        user_id=user_id,
    )
    if status == "ready":
        repo.mark_ready(document_id, 10, 40)
    elif status == "failed":
        repo.mark_failed(document_id, "fallo de indexación")
    return key


def seed_index(vector_root, document_id: str) -> None:
    """Creates a fake FAISS index directory for one document."""
    store_dir = vector_root / document_id
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "index.faiss").write_bytes(b"fake-index")
    (store_dir / "metadata.json").write_text("{}", encoding="utf-8")


def test_unauthenticated_delete_returns_401(repo, storage, vector_store_dir):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id)

    response = client.delete(f"/api/v1/documents/{document_id}")

    assert response.status_code == 401
    assert repo.get_document(document_id) is not None
    assert storage.deleted_keys == []


def test_delete_removes_row_index_and_cache(repo, storage, vector_store_dir):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id)
    seed_index(vector_store_dir, document_id)
    vector_store_service._store_cache[document_id] = object()

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {create_access_token(OWNER_ID, OWNER_EMAIL, 'Ana Martinez', 'Instructor')}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["row_deleted"] is True
    assert body["vector_store_removed"] is True

    # The metadata row is gone, so the list no longer shows the document.
    assert repo.get_document(document_id) is None
    assert all(record.document_id != document_id for record in repo.list_documents(OWNER_ID))

    # The index directory is gone and the store cache no longer holds it.
    assert not (vector_store_dir / document_id).exists()
    assert document_id not in vector_store_service._store_cache


def test_delete_uses_the_row_object_key(repo, storage, vector_store_dir):
    document_id = str(uuid.uuid4())
    object_key = insert_document(repo, document_id)

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {create_access_token(OWNER_ID, OWNER_EMAIL, 'Ana Martinez', 'Instructor')}"},
    )

    assert response.status_code == 200
    assert storage.deleted_keys == [object_key]
    # The key stored in the row is the only one used; nothing is rebuilt.
    assert response.json()["object_key"] == object_key
    assert len(storage.deleted_keys) == 1


def test_storage_failure_keeps_the_row(repo, monkeypatch, vector_store_dir):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id)
    seed_index(vector_store_dir, document_id)

    failing = FakeStorage(error=RuntimeError("OCI Object Storage unavailable"))
    monkeypatch.setattr(
        "app.services.document_deletion_service.get_document_storage",
        lambda: failing,
    )

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {create_access_token(OWNER_ID, OWNER_EMAIL, 'Ana Martinez', 'Instructor')}"},
    )

    assert response.status_code == 502
    # Nothing was deleted, so the user can retry the same request.
    assert repo.get_document(document_id) is not None
    assert (vector_store_dir / document_id).exists()


def test_index_failure_keeps_the_row(repo, storage, monkeypatch, vector_store_dir):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id)

    def _boom(document_id: str) -> bool:
        raise OSError("the index directory is locked")

    monkeypatch.setattr("app.services.document_deletion_service.delete_store", _boom)

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {create_access_token(OWNER_ID, OWNER_EMAIL, 'Ana Martinez', 'Instructor')}"},
    )

    assert response.status_code == 500
    assert repo.get_document(document_id) is not None


def test_foreign_document_is_reported_as_missing(repo, storage, vector_store_dir, auth_headers_other):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id, user_id=OWNER_ID)

    response = client.delete(f"/api/v1/documents/{document_id}", headers=auth_headers_other)

    assert response.status_code == 404
    assert repo.get_document(document_id) is not None
    assert storage.deleted_keys == []


def test_processing_document_is_refused(repo, storage, vector_store_dir, auth_headers_owner):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id, status="processing")

    response = client.delete(f"/api/v1/documents/{document_id}", headers=auth_headers_owner)

    assert response.status_code == 409
    assert repo.get_document(document_id) is not None
    assert storage.deleted_keys == []


def test_unknown_document_is_reported_as_missing(repo, storage, vector_store_dir, auth_headers_owner):
    response = client.delete(f"/api/v1/documents/{uuid.uuid4()}", headers=auth_headers_owner)

    assert response.status_code == 404


def test_deleting_twice_reports_the_document_as_missing(repo, storage, vector_store_dir, auth_headers_owner):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id)

    first = client.delete(f"/api/v1/documents/{document_id}", headers=auth_headers_owner)
    second = client.delete(f"/api/v1/documents/{document_id}", headers=auth_headers_owner)

    assert first.status_code == 200
    assert second.status_code == 404


class FakeOCIStorageService:
    """OCI service double that records the objects it was asked to delete."""

    def __init__(self, is_connected: bool = False):
        self.is_connected = is_connected
        self.deleted: list[tuple[str, str | None]] = []

    def delete_file(self, object_name: str, bucket_name: str | None = None) -> bool:
        self.deleted.append((object_name, bucket_name))
        return True


def make_oci_adapter(service) -> OCIStorageAdapter:
    """Builds an adapter around a fake service, without touching OCI."""
    adapter = OCIStorageAdapter.__new__(OCIStorageAdapter)
    adapter.service = service
    return adapter


def fake_settings(backend: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        resolve_storage_backend=lambda: backend,
        OCI_BUCKET_DOCS="nuevamente-documentos-fuente",
    )


def test_oci_adapter_refuses_to_delete_while_the_connection_is_down(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_storage_service.settings", fake_settings("oci")
    )
    service = FakeOCIStorageService(is_connected=False)
    adapter = make_oci_adapter(service)

    with pytest.raises(RuntimeError):
        adapter.delete_document("usuarios/usr_ana_001/documentos/x.pdf")

    assert service.deleted == []


def test_oci_adapter_deletes_from_the_local_disk_in_local_mode(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_storage_service.settings", fake_settings("local")
    )
    service = FakeOCIStorageService(is_connected=False)
    adapter = make_oci_adapter(service)

    adapter.delete_document("usuarios/usr_ana_001/documentos/x.pdf")

    assert service.deleted == [
        ("usuarios/usr_ana_001/documentos/x.pdf", "nuevamente-documentos-fuente")
    ]


def test_oci_adapter_deletes_from_oci_when_connected(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_storage_service.settings", fake_settings("oci")
    )
    service = FakeOCIStorageService(is_connected=True)
    adapter = make_oci_adapter(service)

    adapter.delete_document("usuarios/usr_ana_001/documentos/x.pdf")

    assert service.deleted == [
        ("usuarios/usr_ana_001/documentos/x.pdf", "nuevamente-documentos-fuente")
    ]


def test_deletion_is_recorded_in_the_audit_log(repo, storage, vector_store_dir, temp_db, auth_headers_owner):
    document_id = str(uuid.uuid4())
    insert_document(repo, document_id)

    response = client.delete(f"/api/v1/documents/{document_id}", headers=auth_headers_owner)

    assert response.status_code == 200
    conn = sqlite3.connect(temp_db)
    try:
        rows = conn.execute(
            "SELECT user_id, action, resource_id FROM audit_log WHERE resource_id = ?",
            (document_id,),
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    assert rows[0][0] == OWNER_ID
    assert rows[0][1] == "delete_document"
    assert rows[0][2] == document_id
