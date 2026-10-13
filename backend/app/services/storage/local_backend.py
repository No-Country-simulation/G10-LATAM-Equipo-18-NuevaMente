"""
local_backend.py

Purpose:
    Local filesystem storage backend for development and testing.
    Only permitted when ALLOW_LOCAL_STORAGE=true in development environments.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.services.storage.base import StorageBackend

logger = logging.getLogger("LocalStorageBackend")


class LocalStorageBackend(StorageBackend):
    """Implementación de almacenamiento local en disco bajo storage_mock/."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or (Path(os.getcwd()) / "storage_mock"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, bucket_name: str, object_name: str) -> Path:
        # Prevenir path traversal
        clean_name = object_name.lstrip("/\\").replace("..", "_")
        target = self.base_dir / bucket_name / clean_name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        logger.warning("WARNING: Almacenando en disco local (desarrollo): [%s/%s].", bucket_name, object_name)
        file_path = self._resolve_path(bucket_name, object_name)
        file_path.write_bytes(data)

        sha256_hash = self.compute_sha256(data)
        meta_file = file_path.with_suffix(file_path.suffix + ".meta.json")
        meta_payload = {
            "content_type": content_type,
            "sha256": sha256_hash,
            "size": len(data),
            "custom_metadata": metadata or {},
        }
        meta_file.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "bucket": bucket_name,
            "objeto_id": object_name,
            "status_upload": "completado",
            "sha256": sha256_hash,
            "storage_provider": "local_mock",
        }

    def head_object(self, bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
        file_path = self._resolve_path(bucket_name, object_name)
        if not file_path.exists():
            return None
        meta_file = file_path.with_suffix(file_path.suffix + ".meta.json")
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "content-length": str(file_path.stat().st_size),
            "opc-meta-sha256": meta.get("sha256", ""),
            "content-type": meta.get("content_type", "application/octet-stream"),
        }

    def get_object(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        file_path = self._resolve_path(bucket_name, object_name)
        if file_path.exists() and file_path.is_file():
            return file_path.read_bytes()
        return None

    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        file_path = self._resolve_path(bucket_name, object_name)
        if file_path.exists():
            try:
                file_path.unlink()
                meta_file = file_path.with_suffix(file_path.suffix + ".meta.json")
                if meta_file.exists():
                    meta_file.unlink()
                return True
            except Exception as e:
                logger.error("Error al eliminar archivo local: %s", e)
                return False
        return True  # Idempotente

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        file_path = self._resolve_path(bucket_name, object_name)
        return file_path.exists()

    def list_objects(self, bucket_name: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        bucket_dir = self.base_dir / bucket_name
        if not bucket_dir.exists():
            return []
        items = []
        for p in bucket_dir.rglob("*"):
            if p.is_file() and not p.name.endswith(".meta.json"):
                rel_name = str(p.relative_to(bucket_dir)).replace("\\", "/")
                if not prefix or rel_name.startswith(prefix):
                    items.append({
                        "name": rel_name,
                        "size": p.stat().st_size,
                        "time_created": str(p.stat().st_mtime),
                    })
        return items
