"""
app.services.storage

Factory and exports for unified storage backends.
"""

from app.core.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.oci_backend import OciStorageBackend
from app.services.storage.local_backend import LocalStorageBackend

_storage_singleton = None


def get_storage_backend() -> StorageBackend:
    """Retorna la instancia configurada de StorageBackend (OCI o Local)."""
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    if settings.OCI_ENABLED:
        try:
            _storage_singleton = OciStorageBackend()
            if _storage_singleton.is_connected:
                return _storage_singleton
        except Exception:
            pass

    if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
        raise RuntimeError("CRITICAL: OCI Object Storage es obligatorio en producción y no se pudo inicializar.")

    _storage_singleton = LocalStorageBackend()
    return _storage_singleton
