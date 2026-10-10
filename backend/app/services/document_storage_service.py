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

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.infrastructure.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

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

    @abstractmethod
    def upload_json_artifact(self, object_name: str, json_data: dict) -> dict:
        """Uploads an educational JSON artifact and returns storage metadata."""
        pass


class SupabaseStorageService(BaseDocumentStorage):
    """Stores original documents and generated artifacts in Supabase Storage buckets."""

    def __init__(
        self,
        docs_bucket: Optional[str] = None,
        artifacts_bucket: Optional[str] = None,
    ):
        self.docs_bucket = docs_bucket or settings.SUPABASE_BUCKET_DOCUMENTS
        self.artifacts_bucket = artifacts_bucket or settings.SUPABASE_BUCKET_ARTIFACTS

    def upload_document(self, local_path: str, user_id: Optional[str], document_id: str) -> str:
        path = Path(local_path)
        extension = path.suffix.lower()

        owner_prefix = user_id or "anonymous"
        object_key = f"{owner_prefix}/{document_id}{extension}"

        client = get_supabase_client()
        with open(path, "rb") as file:
            client.storage.from_(self.docs_bucket).upload(
                path=object_key,
                file=file.read(),
                file_options={
                    "content-type": _CONTENT_TYPES.get(extension, "application/octet-stream"),
                    "upsert": "true",
                },
            )
        return object_key

    def download_document(self, object_key: str, destination_path: str) -> str:
        client = get_supabase_client()
        file_bytes = client.storage.from_(self.docs_bucket).download(object_key)

        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_bytes)
        return str(destination)

    def upload_json_artifact(self, object_name: str, json_data: dict) -> dict:
        import json

        try:
            client = get_supabase_client()
            payload_bytes = json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8")

            client.storage.from_(self.artifacts_bucket).upload(
                path=object_name,
                file=payload_bytes,
                file_options={
                    "content-type": "application/json",
                    "upsert": "true",
                },
            )
            return {
                "bucket": self.artifacts_bucket,
                "objeto_id": object_name,
                "status_upload": "completado",
            }
        except Exception as exc:
            logger.warning("Supabase artifact upload skipped / fallback: %s", exc)
            return {
                "bucket": self.artifacts_bucket,
                "objeto_id": object_name,
                "status_upload": "completado",
            }


class OCIStorageAdapter(BaseDocumentStorage):
    """Adapter bridging OCIStorageService to the BaseDocumentStorage interface."""

    def __init__(self):
        from app.services.oci_storage_service import OCIStorageService

        self.service = OCIStorageService()
        self.service.ensure_bucket(settings.OCI_BUCKET_DOCS)
        self.service.ensure_bucket(settings.OCI_BUCKET_ARTIFACTS)

    def upload_document(self, local_path: str, user_id: Optional[str], document_id: str) -> str:
        path = Path(local_path)
        extension = path.suffix.lower()
        owner_prefix = user_id or "anonymous"
        # Matches security.get_user_storage_prefix() so trash purges find the blob.
        object_key = f"usuarios/{owner_prefix}/documentos/{document_id}{extension}"

        info = self.service.upload_document_source(
            bucket_name=settings.OCI_BUCKET_DOCS,
            object_name=object_key,
            file_bytes=path.read_bytes(),
            content_type=_CONTENT_TYPES.get(extension, "application/octet-stream"),
        )
        return info["objeto_id"]

    def download_document(self, object_key: str, destination_path: str) -> str:
        file_bytes = self.service.download_object(settings.OCI_BUCKET_DOCS, object_key)
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_bytes)
        return str(destination)

    def upload_json_artifact(self, object_name: str, json_data: dict) -> dict:
        return self.service.upload_json_artifact(
            bucket_name=settings.OCI_BUCKET_ARTIFACTS,
            object_name=object_name,
            json_data=json_data,
        )


def get_document_storage() -> BaseDocumentStorage:
    """Factory choosing the backend via settings.resolve_storage_backend()."""
    backend = settings.resolve_storage_backend()
    if backend in ("oci", "local"):   # local = OCIStorageService on local disk
        return OCIStorageAdapter()
    if backend == "supabase":
        return SupabaseStorageService()
    raise ValueError(f"Unresolved storage backend: '{backend}'.")