import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.config import settings
from app.services.storage import get_storage_backend
from app.services.storage.base import StorageBackend

logger = logging.getLogger("OCIStorageService")


class OCIStorageService:
    """
    Servicio de alto nivel para almacenamiento en OCI Object Storage Always Free.
    Delega en StorageBackend (Instance Principals o Config File en OCI, o Local en dev).
    Garantiza el esquema jerárquico:
      - Documentos: usuarios/{user_id}/documentos/{sha256}/{nombre_saneado}
      - Contenidos: usuarios/{user_id}/contenidos/{content_id}/v{n}.json
    """

    def __init__(self):
        self.backend: StorageBackend = get_storage_backend()
        self.is_connected = getattr(self.backend, "is_connected", True)
        self.namespace = getattr(self.backend, "namespace", settings.OCI_NAMESPACE or "mock-namespace")

    def upload_json_artifact(
        self,
        bucket_name: str,
        object_name: str,
        json_data: dict,
        user_id: Optional[str] = None,
        version: int = 1,
        doc_slug: Optional[str] = None,
        recipient_profile: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Guarda los contenidos educativos adaptados (JSON) en el bucket de OCI Object Storage Always Free
        con trazabilidad completa.
        """
        if object_name.startswith("usuarios/"):
            target_key = object_name
        else:
            content_id = object_name.replace(".json", "")
            target_key = StorageBackend.build_content_key(
                user_id=user_id,
                content_id=content_id,
                version=version,
                doc_slug=doc_slug,
                recipient_profile=recipient_profile,
                output_format=output_format,
            )

        body_bytes = json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8")
        metadata = {
            "trazabilidad-tipo": "contenido_educativo",
            "version": str(version),
            "user-id": StorageBackend.sanitize_user_id(user_id),
        }
        if doc_slug:
            metadata["documento-origen"] = doc_slug
        if recipient_profile:
            metadata["perfil-destinatario"] = recipient_profile
        if output_format:
            metadata["formato-salida"] = output_format

        try:
            res = self.backend.put_object(
                bucket_name=bucket_name,
                object_name=target_key,
                data=body_bytes,
                content_type="application/json",
                metadata=metadata,
            )
            return {
                "bucket": bucket_name,
                "objeto_id": target_key,
                "status_upload": "completado",
                "sha256": res.get("sha256"),
            }
        except Exception as exc:
            logger.error("Error al persistir artefacto educativo en OCI [%s/%s]: %s", bucket_name, target_key, exc)
            if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
                raise
            return {
                "bucket": bucket_name,
                "objeto_id": target_key,
                "status_upload": "error",
                "error": str(exc),
            }

    def upload_document_source(
        self,
        bucket_name: str,
        object_name: str,
        file_bytes: bytes,
        content_type: str = "application/pdf",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Guarda los documentos técnicos originales subidos (PDF, TXT, MD) en OCI Object Storage Always Free.
        """
        sha256_hash = StorageBackend.compute_sha256(file_bytes)

        if object_name.startswith("usuarios/"):
            target_key = object_name
        else:
            target_key = StorageBackend.build_document_key(user_id, sha256_hash, object_name)

        clean_name = StorageBackend.sanitize_filename(object_name)
        metadata = {
            "trazabilidad-tipo": "documento_fuente",
            "nombre-original": clean_name,
            "sha256": sha256_hash,
            "user-id": StorageBackend.sanitize_user_id(user_id),
        }

        try:
            res = self.backend.put_object(
                bucket_name=bucket_name,
                object_name=target_key,
                data=file_bytes,
                content_type=content_type,
                metadata=metadata,
            )
            return {
                "bucket": bucket_name,
                "objeto_id": target_key,
                "status_upload": "completado",
                "sha256": sha256_hash,
                "deduplicado": res.get("deduplicado", False),
            }
        except Exception as exc:
            logger.error("Error al persistir documento fuente en OCI [%s/%s]: %s", bucket_name, target_key, exc)
            if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
                raise
            return {
                "bucket": bucket_name,
                "objeto_id": target_key,
                "status_upload": "error",
                "error": str(exc),
            }

    def download_document_source(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """
        Descarga documentos técnicos u objetos desde OCI Object Storage Always Free.
        """
        return self.backend.get_object(bucket_name, object_name)

    def delete_document(self, bucket_name: str, object_name: str) -> bool:
        """
        Elimina un documento de OCI de forma idempotente.
        """
        return self.backend.delete_object(bucket_name, object_name)

    def delete_file(self, object_name: str, bucket_name: Optional[str] = None) -> bool:
        """
        Elimina un archivo u objeto de OCI de forma idempotente (usado por trash_service y purga).
        """
        target_bucket = bucket_name or (
            settings.OCI_BUCKET_DOCS if "documentos" in object_name else settings.OCI_BUCKET_ARTIFACTS
        )
        return self.backend.delete_object(target_bucket, object_name)

    def ensure_bucket(self, bucket_name: str) -> None:
        """Asegura la disponibilidad del bucket."""
        pass

    def download_object(self, bucket_name: str, object_name: str) -> bytes:
        """Descarga el contenido del objeto o lanza FileNotFoundError si no existe."""
        data = self.backend.get_object(bucket_name, object_name)
        if data is None:
            raise FileNotFoundError(f"{bucket_name}/{object_name} no encontrado.")
        return data

    def health(self) -> Dict[str, Any]:
        """Reporte de salud del servicio de almacenamiento."""
        return {
            "connected": getattr(self.backend, "is_connected", True),
            "namespace": self.namespace,
            "mode": getattr(self.backend, "auth_mode", "oci"),
        }
