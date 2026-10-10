"""
oci_storage_service.py

Purpose:
    Storage for OCI Object Storage (Always Free): uploads original documents
    and educational JSON artifacts, downloads objects, and deletes them (used
    by the trash flow). When OCI is not configured it degrades to a local-disk
    store under settings.LOCAL_STORAGE_DIR (last-resort fallback).

Input:
    - upload_*: bucket name, object name and payload (bytes / dict).
    - download_object: bucket name + object name.
    - delete_file: object name (+ optional bucket; tries all configured buckets).

Output:
    - uploads -> {"bucket", "objeto_id", "status_upload"} (Spanish keys kept for
      compatibility with adaptation responses).
    - download_object -> bytes; delete_file -> bool; ensure_bucket -> None.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.infrastructure.oci_client import get_oci_client, get_oci_namespace,  get_oci_compartment_id

logger = logging.getLogger("OCIStorageService")


class OCIStorageService:
    """Wraps the cached OCI client; falls back to local disk when OCI is
    unavailable."""

    def __init__(self):
        self.client = get_oci_client()
        self.namespace = get_oci_namespace() or "mock-oci-namespace"
        self.is_connected = self.client is not None
        if not self.is_connected:
            logger.info(
                "OCI not configured; storing locally under %s.", settings.LOCAL_STORAGE_DIR
            )

    @property
    def LOCAL_DIR(self) -> Path:
        return Path(settings.LOCAL_STORAGE_DIR)

    def _mock_path(self, bucket_name: str, object_name: str) -> Path:
        return self.LOCAL_DIR / bucket_name / object_name

    def _mock_write(self, bucket_name: str, object_name: str, data: bytes) -> Dict[str, Any]:
        path = self._mock_path(bucket_name, object_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"bucket": bucket_name, "objeto_id": object_name, "status_upload": "completado"}

    # ── bucket provisioning ────────────────────────────────────────────────
    def ensure_bucket(self, bucket_name: str) -> None:
        """Creates the bucket if it does not exist (no-op in local mode)."""
        if not self.is_connected:
            self._mock_path(bucket_name, ".").parent.mkdir(parents=True, exist_ok=True)
            return
        import oci
        try:
            self.client.get_bucket(self.namespace, bucket_name)
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                details = oci.object_storage.models.CreateBucketDetails(name=bucket_name,
                    compartment_id=get_oci_compartment_id())
                self.client.create_bucket(self.namespace, details)
                logger.info("Created OCI bucket %s.", bucket_name)
            else:
                raise

    # ── uploads ────────────────────────────────────────────────────────────
    def upload_json_artifact(self, bucket_name: str, object_name: str,
                             json_data: dict) -> Dict[str, Any]:
        """Stores an educational JSON artifact in the configured bucket."""
        body = json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8")
        if self.is_connected:
            try:
                self.client.put_object(self.namespace, bucket_name, object_name,
                                       body, content_type="application/json")
                return {"bucket": bucket_name, "objeto_id": object_name, "status_upload": "completado"}
            except Exception as exc:
                logger.error("OCI JSON upload failed; storing locally: %s", exc)
        return self._mock_write(bucket_name, object_name, body)

    def upload_document_source(self, bucket_name: str, object_name: str,
                               file_bytes: bytes,
                               content_type: str = "application/pdf") -> Dict[str, Any]:
        """Stores the original uploaded document (PDF/MD/TXT)."""
        if self.is_connected:
            try:
                self.client.put_object(self.namespace, bucket_name, object_name,
                                       file_bytes, content_type=content_type)
                return {"bucket": bucket_name, "objeto_id": object_name, "status_upload": "completado"}
            except Exception as exc:
                logger.error("OCI document upload failed; storing locally: %s", exc)
        return self._mock_write(bucket_name, object_name, file_bytes)

    # ── download ─────────────────────────
    def download_object(self, bucket_name: str, object_name: str) -> bytes:
        """Returns the object bytes from OCI (or from the local fallback)."""
        if self.is_connected:
            response = self.client.get_object(self.namespace, bucket_name, object_name)
            return response.data.content
        path = self._mock_path(bucket_name, object_name)
        if not path.exists():
            raise FileNotFoundError(f"{bucket_name}/{object_name} not found locally.")
        return path.read_bytes()

    # ── delete ───────────────────────────
    def delete_file(self, object_name: str, bucket_name: Optional[str] = None) -> bool:
        """Deletes an object. Without bucket_name it tries every configured
        bucket. Raises on real OCI errors so callers can flag purge failure."""
        buckets = [bucket_name] if bucket_name else [
            settings.OCI_BUCKET_DOCS, settings.OCI_BUCKET_ARTIFACTS
        ]
        if self.is_connected:
            import oci
            for bucket in buckets:
                try:
                    self.client.delete_object(self.namespace, bucket, object_name)
                except oci.exceptions.ServiceError as exc:
                    if exc.status != 404:   # 404 = already gone, not a failure
                        raise
            return True
        for bucket in buckets:
            path = self._mock_path(bucket, object_name)
            if path.exists():
                path.unlink()
        return True

    def health(self) -> Dict[str, Any]:
        return {"connected": self.is_connected, "namespace": self.namespace,
                "mode": "oci" if self.is_connected else "local_disk"}