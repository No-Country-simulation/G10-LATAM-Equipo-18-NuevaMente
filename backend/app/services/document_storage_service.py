"""
document_storage_service.py

Purpose:
    Storage abstraction for the original uploaded document (PDF/MD/TXT) —
    a separate concern from the vector store (embeddings, per document_id)
    and from document_repository (metadata rows: title, status, etc.).
    Supabase Storage is the first implementation; an OCI-backed one can be
    added later behind the same interface without changing
    document_pipeline_service.py, which only depends on BaseDocumentStorage.

Input:
    - upload_document: a local file path, an optional user_id (None until
      login exists), and a document_id.
    - download_document: an object_key (as returned by upload_document) and
      a local destination path.

Output:
    - upload_document -> object_key (str): identifies the stored file,
      persisted in the documents table's object_key column.
    - download_document -> str: local path where the file was written.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.infrastructure.supabase_client import get_supabase_client

_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


class BaseDocumentStorage(ABC):
    """Contract every storage backend (Supabase, OCI) must implement."""

    @abstractmethod
    def upload_document(self, local_path: str, user_id: Optional[str], document_id: str) -> str:
        """Uploads the original document and returns its object_key."""
        pass

    @abstractmethod
    def download_document(self, object_key: str, destination_path: str) -> str:
        """Downloads a previously uploaded document to destination_path."""
        pass


class SupabaseStorageService(BaseDocumentStorage):
    """Stores original documents in a Supabase Storage bucket."""

    def __init__(self, bucket: Optional[str] = None):
        self.bucket = bucket or settings.SUPABASE_BUCKET_DOCUMENTS

    def upload_document(self, local_path: str, user_id: Optional[str], document_id: str) -> str:
        path = Path(local_path)
        extension = path.suffix.lower()

        # Layout: {owner}/{document_id}{extension}. "anonymous" until login
        # exists — once it does, user_id being non-null naturally scopes
        # each user's documents under their own prefix.
        owner_prefix = user_id or "anonymous"
        object_key = f"{owner_prefix}/{document_id}{extension}"

        client = get_supabase_client()
        with open(path, "rb") as file:
            client.storage.from_(self.bucket).upload(
                path=object_key,
                file=file.read(),
                file_options={
                    "content-type": _CONTENT_TYPES.get(extension, "application/octet-stream"),
                    # Allows re-processing the same document_id without a manual delete first.
                    "upsert": "true",
                },
            )
        return object_key

    def download_document(self, object_key: str, destination_path: str) -> str:
        client = get_supabase_client()
        file_bytes = client.storage.from_(self.bucket).download(object_key)

        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_bytes)
        return str(destination)


def get_document_storage() -> BaseDocumentStorage:
    """Factory choosing the storage backend by settings.STORAGE_METHOD."""
    if settings.STORAGE_METHOD == "supabase":
        return SupabaseStorageService()
    raise ValueError(
        f"Unsupported STORAGE_METHOD: '{settings.STORAGE_METHOD}'. "
        "An OCI-backed BaseDocumentStorage implementation is still pending."
    )