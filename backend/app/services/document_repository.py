"""
document_repository.py

Purpose:
    Metadata store for uploaded documents — tracks title, where the original
    file lives (object_key), and processing status (processing/ready/failed).
    Separate from document_storage_service.py (which moves the file bytes)
    and from vector_store_service.py (which holds the RAG index): this is
    just the row a document-listing endpoint would query.

Input:
    document_id, title, source_filename, object_key, user_id (optional,
    None until login exists) to create a row; document_id to update or
    fetch one; an optional user_id to filter a list.

Output:
    DocumentRecord instances (schemas/document_record.py), or None when a
    single lookup finds nothing.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.core.config import settings
from app.core.security import get_db
from app.infrastructure.supabase_client import get_supabase_client
from app.schemas.document_record import (
    DocumentRecord,
    STATUS_PROCESSING,
    STATUS_READY,
    STATUS_FAILED,
)

_TABLE_NAME = "documents"


def _require_valid_uuid(value: str, field_name: str) -> None:
    """Validates that value looks like a UUID before it reaches Postgres.
    document_id and user_id are both `uuid`-typed columns — without this
    check, a malformed value surfaces as a raw, unfriendly
    postgrest.exceptions.APIError deep inside the client library instead
    of a clear message pointing at the actual mistake."""
    try:
        UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise ValueError(
            f"'{value}' is not a valid {field_name} — expected a UUID string."
        )


class BaseDocumentRepository(ABC):
    """Contract every metadata backend (Supabase, or a future local/JSON
    implementation) must implement."""

    @abstractmethod
    def create_document(
        self,
        document_id: str,
        title: str,
        source_filename: str,
        object_key: str,
        user_id: Optional[str] = None,
    ) -> DocumentRecord:
        """Inserts a new row with status=processing."""
        pass

    @abstractmethod
    def mark_ready(self, document_id: str, total_parents: int, total_children: int) -> None:
        """Marks a document as fully indexed and ready for content generation."""
        pass

    @abstractmethod
    def mark_failed(self, document_id: str, error_message: str) -> None:
        """Marks a document as failed, recording why."""
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """Returns a single document's record, or None if it doesn't exist."""
        pass

    @abstractmethod
    def list_documents(self, user_id: Optional[str] = None) -> List[DocumentRecord]:
        """Lists documents, newest first. Without login, user_id is None and
        every document is returned — there's no owner to filter by yet."""
        pass


class SupabaseDocumentRepository(BaseDocumentRepository):
    """Stores document metadata in a Supabase Postgres table."""

    def create_document(
        self,
        document_id: str,
        title: str,
        source_filename: str,
        object_key: str,
        user_id: Optional[str] = None,
    ) -> DocumentRecord:
        _require_valid_uuid(document_id, "document_id")
        if user_id is not None:
            _require_valid_uuid(user_id, "user_id")

        client = get_supabase_client()
        row = {
            "document_id": document_id,
            "user_id": user_id,
            "title": title,
            "source_filename": source_filename,
            "object_key": object_key,
        }
        response = client.table(_TABLE_NAME).insert(row).execute()

        # response.data can come back empty or malformed if the insert
        # succeeded at the HTTP level but Supabase didn't echo the row back
        # as expected — indexing response.data[0] directly would then raise
        # an unhelpful IndexError/TypeError instead of a clear error.
        if response.data and isinstance(response.data[0], dict):
            return DocumentRecord(**response.data[0])

        raise RuntimeError("Supabase did not return a valid object when inserting the document.")

    def mark_ready(self, document_id: str, total_parents: int, total_children: int) -> None:
        _require_valid_uuid(document_id, "document_id")
        client = get_supabase_client()
        client.table(_TABLE_NAME).update({
            "status": STATUS_READY,
            "total_parents": total_parents,
            "total_children": total_children,
            "updated_at": self._now_iso(),
        }).eq("document_id", document_id).execute()

    def mark_failed(self, document_id: str, error_message: str) -> None:
        _require_valid_uuid(document_id, "document_id")
        client = get_supabase_client()
        client.table(_TABLE_NAME).update({
            "status": STATUS_FAILED,
            "error_message": error_message,
            "updated_at": self._now_iso(),
        }).eq("document_id", document_id).execute()

    def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        _require_valid_uuid(document_id, "document_id")
        client = get_supabase_client()
        response = client.table(_TABLE_NAME).select("*").eq("document_id", document_id).execute()

        if response.data and isinstance(response.data[0], dict):
            return DocumentRecord(**response.data[0])
        return None

    def list_documents(self, user_id: Optional[str] = None) -> List[DocumentRecord]:
        if user_id is not None:
            _require_valid_uuid(user_id, "user_id")
        client = get_supabase_client()
        query = client.table(_TABLE_NAME).select("*").order("created_at", desc=True)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        response = query.execute()

        # Skips any row that isn't a proper dict instead of raising —
        # one malformed row from Supabase shouldn't break the whole listing.
        return [
            DocumentRecord(**row)
            for row in response.data
            if isinstance(row, dict)
        ]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

_DOCUMENTS_DDL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    object_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    total_parents INTEGER,
    total_children INTEGER,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

class SQLiteDocumentRepository(BaseDocumentRepository):
    """Documents metadata in the local SQLite db (users.db), used when the
    effective backend is OCI or local disk — Object Storage has no tables."""

    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        conn = get_db()
        try:
            conn.execute(_DOCUMENTS_DDL)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents (user_id)")
            conn.commit()
        finally:
            conn.close()

    def create_document(self, document_id, title, source_filename, object_key, user_id=None):
        now = self._now_iso()
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO documents (document_id, user_id, title, source_filename, object_key,"
                " status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (document_id, user_id, title, source_filename, object_key,
                 STATUS_PROCESSING, now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        finally:
            conn.close()
        return DocumentRecord(**dict(row))

    def mark_ready(self, document_id, total_parents, total_children):
        self._update(document_id, status=STATUS_READY,
                     total_parents=total_parents, total_children=total_children)

    def mark_failed(self, document_id, error_message):
        self._update(document_id, status=STATUS_FAILED, error_message=error_message)

    def get_document(self, document_id):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        finally:
            conn.close()
        return DocumentRecord(**dict(row)) if row else None

    def list_documents(self, user_id=None):
        conn = get_db()
        try:
            if user_id is not None:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM documents ORDER BY created_at DESC"
                ).fetchall()
        finally:
            conn.close()
        return [DocumentRecord(**dict(r)) for r in rows]

    def _update(self, document_id, **fields):
        fields["updated_at"] = self._now_iso()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        conn = get_db()
        try:
            conn.execute(f"UPDATE documents SET {assignments} WHERE document_id = ?",
                         (*fields.values(), document_id))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

def get_document_repository() -> BaseDocumentRepository:
    """Metadata backend follows the same resolution as blob storage, because
    a document's row must live where its file does."""
    backend = settings.resolve_storage_backend()
    if backend in ("oci", "local"):
        return SQLiteDocumentRepository()
    if backend == "supabase":
        return SupabaseDocumentRepository()
    raise ValueError(f"Unresolved storage backend: '{backend}'.")