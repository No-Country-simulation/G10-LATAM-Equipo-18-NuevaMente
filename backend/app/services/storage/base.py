"""
base.py

Purpose:
    Abstract base interface and key naming utilities for NuevaMente document
    and educational artifact storage backends (OCI Object Storage & Local).
"""

from abc import ABC, abstractmethod
import hashlib
import re
import unicodedata
from datetime import datetime, timezone
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
    def build_document_key(cls, user_id: Optional[str], sha256_hash: str, filename: str) -> str:
        """
        Construye la clave jerárquica para un documento fuente:
        usuarios/{user_id}/documentos/{sha256}/{nombre_saneado}
        """
        safe_user = cls.sanitize_user_id(user_id)
        safe_name = cls.sanitize_filename(filename)
        return f"usuarios/{safe_user}/documentos/{sha256_hash}/{safe_name}"

    @staticmethod
    def slugify_label(text: Optional[str], max_len: int = 40) -> str:
        """
        Convierte un texto (formato de salida, título) en un slug legible para
        usarlo dentro de la clave del objeto: minúsculas, sin acentos ni
        caracteres especiales, separados por guiones.
        """
        if not text:
            return ""
        ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
        return slug[:max_len].strip("-")

    @classmethod
    def build_content_key(
        cls,
        user_id: Optional[str],
        content_id: str,
        version: int = 1,
        output_format: Optional[str] = None,
        document_title: Optional[str] = None,
        recipient_profile: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> str:
        """
        Construye la clave jerárquica para un artefacto educativo JSON:
        usuarios/{user_id}/contenidos/{content_id}/{titulo}-{formato}-{perfil}-{yyyymmdd}[-v{version}].json

        El nombre identifica el objeto en la consola de OCI y en la columna
        object_key_json de Supabase: título del documento, formato de salida,
        perfil del destinatario y fecha de creación (UTC, AAAAMMDD).
        La versión solo se añade cuando es superior a 1 ("Ampliar") para no
        sobrescribir el artefacto generado el mismo día. Sin metadatos
        (registros antiguos / script de migración) se conserva v{version}.json.
        """
        safe_user = cls.sanitize_user_id(user_id)
        clean_content_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", content_id).strip("_")
        title_slug = cls.slugify_label(document_title, max_len=40)
        fmt_slug = cls.slugify_label(output_format, max_len=20)
        profile_slug = cls.slugify_label(recipient_profile, max_len=20)
        label = "-".join(part for part in (title_slug, fmt_slug, profile_slug) if part)
        if not label:
            return f"usuarios/{safe_user}/contenidos/{clean_content_id}/v{version}.json"
        stamp = (created_at or datetime.now(timezone.utc)).strftime("%Y%m%d")
        suffix = f"-v{version}" if version > 1 else ""
        filename = f"{label}-{stamp}{suffix}.json"
        return f"usuarios/{safe_user}/contenidos/{clean_content_id}/{filename}"
