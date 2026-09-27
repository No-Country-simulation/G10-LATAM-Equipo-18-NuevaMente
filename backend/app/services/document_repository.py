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

from app.core.config import settings
from app.infrastructure.supabase_client import get_supabase_client
from app.schemas.document_record import (
    DocumentRecord,
    STATUS_READY,
    STATUS_FAILED,
)

_TABLE_NAME = "documents"


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
        client = get_supabase_client()
        row = {
            "document_id": document_id,
            "user_id": user_id,
            "title": title,
            "source_filename": source_filename,
            "object_key": object_key,
        }
        response = client.table(_TABLE_NAME).insert(row).execute()
        if response.data and isinstance(response.data[0], dict):
            return DocumentRecord(**response.data[0])
        raise RuntimeError("Supabase did not return a valid object when inserting the document.")

    def mark_ready(self, document_id: str, total_parents: int, total_children: int) -> None:
        client = get_supabase_client()
        client.table(_TABLE_NAME).update({
            "status": STATUS_READY,
            "total_parents": total_parents,
            "total_children": total_children,
            "updated_at": self._now_iso(),
        }).eq("document_id", document_id).execute()

    def mark_failed(self, document_id: str, error_message: str) -> None:
        client = get_supabase_client()
        client.table(_TABLE_NAME).update({
            "status": STATUS_FAILED,
            "error_message": error_message,
            "updated_at": self._now_iso(),
        }).eq("document_id", document_id).execute()

    def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        client = get_supabase_client()
        response = client.table(_TABLE_NAME).select("*").eq("document_id", document_id).execute()
        if not response.data:
            return None
        record_data = response.data[0]
        if isinstance(record_data, dict):
            return DocumentRecord(**record_data)
        raise RuntimeError(f"Unexpected data format received for document_id '{document_id}'.")

    def list_documents(self, user_id: Optional[str] = None) -> List[DocumentRecord]:
        client = get_supabase_client()
        query = client.table(_TABLE_NAME).select("*").order("created_at", desc=True)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        response = query.execute()
        documents = []
        for row in response.data:
            if isinstance(row, dict):
                documents.append(DocumentRecord(**row))
            else:
                raise RuntimeError("Unexpected data format encountered in documents list.")

        return documents

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def get_document_repository() -> BaseDocumentRepository:
    """Factory choosing the metadata backend by settings.STORAGE_METHOD —
    kept in step with get_document_storage() since both back the same
    per-document pipeline state."""
    if settings.STORAGE_METHOD == "supabase":
        return SupabaseDocumentRepository()
    raise ValueError(
        f"Unsupported STORAGE_METHOD: '{settings.STORAGE_METHOD}'. "
        "A local/JSON BaseDocumentRepository implementation is still pending."
    )