"""
app.services.storage

Factory and exports for unified storage backends.
"""

import logging
from app.core.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.oci_backend import OciStorageBackend
from app.services.storage.local_backend import LocalStorageBackend

logger = logging.getLogger("StorageBackendFactory")
_storage_singleton = None


def reset_storage_backend() -> None:
    """Restablece el singleton para pruebas unitarias."""
    global _storage_singleton
    _storage_singleton = None


def get_storage_backend() -> StorageBackend:
    """Retorna la instancia configurada de StorageBackend (OCI o Local)."""
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    if settings.OCI_ENABLED:
        try:
            candidate = OciStorageBackend()
            if candidate.is_connected:
                _storage_singleton = candidate
                return _storage_singleton
        except Exception as exc:
            if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
                logger.critical("CRITICAL: Fallo inicializando OCI en producción: %s", exc)
                raise RuntimeError(f"CRITICAL: OCI Object Storage es obligatorio en producción: {exc}")

    if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
        raise RuntimeError("CRITICAL: OCI Object Storage es obligatorio en producción y no se pudo inicializar.")

    logger.warning("WARNING: Operando con LocalStorageBackend (modo local / desarrollo).")
    _storage_singleton = LocalStorageBackend()
    return _storage_singleton
