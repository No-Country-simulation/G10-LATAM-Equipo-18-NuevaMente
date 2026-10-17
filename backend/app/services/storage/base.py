"""
base.py

Purpose:
    Abstract base interface and key naming utilities for NuevaMente document
    and educational artifact storage backends (OCI Object Storage & Local).
"""

from abc import ABC, abstractmethod
import hashlib
import re
from typing import Dict, Any, Optional, List


class StorageBackend(ABC):
    """Contrato base para backends de almacenamiento en la nube o local."""

    @abstractmethod
    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Sube un objeto al bucket. Retorna metadata del objeto subido."""
        pass

    @abstractmethod
    def head_object(self, bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
        """Retorna metadatos del objeto si existe, o None."""
        pass

    @abstractmethod
    def get_object(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """Descarga el contenido binario del objeto o retorna None si no existe."""
        pass

    @abstractmethod
    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """Elimina un objeto de forma idempotente (404 / no existe = True)."""
        pass

    @abstractmethod
    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Verifica si el objeto existe."""
        pass

    @abstractmethod
    def list_objects(self, bucket_name: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista objetos en el bucket con prefijo opcional."""
        pass

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Calcula el hash SHA-256 de los bytes provistos."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Sanea el nombre de un archivo removiendo rutas ('..', '/'),
        caracteres especiales y espacios, garantizando compatibilidad ASCII.
        """
        # Extraer nombre base si viene con ruta
        base = name.split("/")[-1].split("\\")[-1]
        # Reemplazar espacios y caracteres no alfanuméricos seguros
        clean = re.sub(r"[^a-zA-Z0-9_\.-]", "_", base)
        # Prevenir múltiples puntos o nombres vacíos
        clean = re.sub(r"\.{2,}", ".", clean).strip("._")
        return clean or "documento_fuente"

    @staticmethod
    def sanitize_user_id(user_id: Optional[str]) -> str:
        """Sanea el identificador de usuario."""
        if not user_id:
            return "anonimo"
        clean = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(user_id)).strip("_")
        return clean or "anonimo"

    @classmethod
    def build_document_key(
        cls,
        user_id: Optional[str],
        sha256_hash: str,
        filename: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Construye la clave jerárquica con trazabilidad profesional para un documento fuente:
        usuarios/{user_id}/documentos/{slug}_{YYYYMMDD}_{hash8}/{nombre_saneado}
        """
        safe_user = cls.sanitize_user_id(user_id)
        safe_name = cls.sanitize_filename(filename)

        # Extraer slug legible del nombre base
        stem = safe_name.rsplit(".", 1)[0] if "." in safe_name else safe_name
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:35].strip("_") or "doc"

        # Fecha en formato compacto ISO UTC (YYYYMMDD)
        if not timestamp:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")

        short_hash = (sha256_hash or "00000000")[:8]
        folder_trace = f"{slug}_{timestamp}_{short_hash}"
        return f"usuarios/{safe_user}/documentos/{folder_trace}/{safe_name}"

    @classmethod
    def build_content_key(
        cls,
        user_id: Optional[str],
        content_id: str,
        version: int = 1,
        doc_slug: Optional[str] = None,
        recipient_profile: Optional[str] = None,
        output_format: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Construye la clave jerárquica con trazabilidad profesional para un artefacto educativo:
        usuarios/{user_id}/contenidos/{carpeta_trazable}/{nombre_archivo_trazable}_v{version}.json
        """
        safe_user = cls.sanitize_user_id(user_id)
        clean_content_id = re.sub(r"[^a-zA-Z0-9_-]", "_", content_id).strip("_")

        # Construir identificador trazable si se disponen metadatos contextuales
        parts = []
        if doc_slug:
            clean_doc = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_slug)[:25].strip("_")
            if clean_doc:
                parts.append(clean_doc)
        if recipient_profile:
            clean_prof = re.sub(r"[^a-zA-Z0-9_-]", "_", recipient_profile)[:15].strip("_")
            if clean_prof:
                parts.append(clean_prof)
        if output_format:
            clean_fmt = re.sub(r"[^a-zA-Z0-9_-]", "_", output_format)[:15].strip("_")
            if clean_fmt:
                parts.append(clean_fmt)

        if not timestamp:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")

        if parts:
            base_trace = "_".join(parts)
            folder_trace = f"{base_trace}_{timestamp}"
            file_name = f"{base_trace}_v{version}.json"
        else:
            folder_trace = clean_content_id
            file_name = f"{clean_content_id}_v{version}.json"

        return f"usuarios/{safe_user}/contenidos/{folder_trace}/{file_name}"
