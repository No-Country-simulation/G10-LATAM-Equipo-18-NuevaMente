"""
test_storage_backend.py

Pruebas unitarias para la arquitectura de almacenamiento OCI Object Storage Always Free.
Verifica:
  - Modo 'auto': Instance Principals con fallback a config_file.
  - Prohibición estricta de fallback silencioso a local en producción.
  - Autochequeo (self_check) de salud de buckets, tier Standard y acceso privado.
  - Comportamiento de 'status_upload' (nunca 'completado' si falla el SDK).
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.storage import get_storage_backend, reset_storage_backend
from app.services.storage.oci_backend import OciStorageBackend
from app.services.storage.local_backend import LocalStorageBackend


@pytest.fixture(autouse=True)
def clean_storage_singleton():
    """Limpia el singleton de almacenamiento antes y después de cada test."""
    reset_storage_backend()
    yield
    reset_storage_backend()


def test_production_raises_on_oci_failure_no_silent_fallback():
    """En producción, si OCI falla y ALLOW_LOCAL_STORAGE=False, debe lanzar RuntimeError."""
    with patch.object(settings, "APP_ENV", "production"), \
         patch.object(settings, "ALLOW_LOCAL_STORAGE", False), \
         patch.object(type(settings), "OCI_ENABLED", new_callable=PropertyMock, return_value=True), \
         patch("app.services.storage.oci_backend.OciStorageBackend._initialize_client", side_effect=RuntimeError("OCI IMDS caido")):
        
        with pytest.raises(RuntimeError) as exc_info:
            get_storage_backend()
        
        assert "CRITICAL" in str(exc_info.value) or "obligatorio" in str(exc_info.value)


def test_development_falls_back_to_local_with_warning():
    """En desarrollo (development), si OCI no está disponible, cae a LocalStorageBackend con log de advertencia."""
    with patch.object(settings, "APP_ENV", "development"), \
         patch.object(settings, "ALLOW_LOCAL_STORAGE", False), \
         patch.object(type(settings), "OCI_ENABLED", new_callable=PropertyMock, return_value=False):
        
        backend = get_storage_backend()
        assert isinstance(backend, LocalStorageBackend)


def test_oci_backend_auto_mode_uses_config_file_when_not_on_vm():
    """En modo 'auto', si no se encuentra IMDS de VM pero existe ~/.oci/config, activa config_file."""
    mock_client = MagicMock()
    mock_client.get_namespace.return_value.data = "test_namespace_123"

    with patch.object(settings, "OCI_AUTH_MODE", "auto"), \
         patch("os.path.exists", return_value=True), \
         patch("oci.config.from_file", return_value={"region": "mx-monterrey-1"}), \
         patch("oci.object_storage.ObjectStorageClient", return_value=mock_client):
        
        backend = OciStorageBackend()
        assert backend.is_connected is True
        assert backend.active_auth_mode == "config_file"
        assert backend.namespace == "test_namespace_123"


def test_oci_self_check_returns_operativo_when_buckets_valid():
    """self_check() valida ambos buckets con tier Standard y NoPublicAccess."""
    mock_client = MagicMock()
    mock_b_fuentes = MagicMock()
    mock_b_fuentes.storage_tier = "Standard"
    mock_b_fuentes.public_access_type = "NoPublicAccess"

    mock_b_contenidos = MagicMock()
    mock_b_contenidos.storage_tier = "Standard"
    mock_b_contenidos.public_access_type = "NoPublicAccess"

    def get_bucket_mock(ns, b_name):
        res = MagicMock()
        if "fuente" in b_name:
            res.data = mock_b_fuentes
        else:
            res.data = mock_b_contenidos
        return res

    mock_client.get_bucket.side_effect = get_bucket_mock

    backend = OciStorageBackend.__new__(OciStorageBackend)
    backend.auth_mode = "instance_principal"
    backend.region = "mx-monterrey-1"
    backend.active_auth_mode = "instance_principal"
    backend.is_connected = True
    backend._client = mock_client
    backend._namespace = "test_ns"
    backend._last_error = None

    report = backend.self_check()
    assert report["status"] == "operativo"
    assert report["auth_mode"] == "instance_principal"
    assert report["namespace"] is True
    assert len(report["buckets"]) == 2
    for b_data in report["buckets"].values():
        assert b_data["alcanzable"] is True
        assert b_data["tier"] == "Standard"
        assert b_data["privado"] is True


def test_oci_self_check_detects_degraded_when_bucket_public():
    """self_check() marca degradado si un bucket no es privado o no es Standard."""
    mock_client = MagicMock()
    mock_b = MagicMock()
    mock_b.storage_tier = "Archive"  # No es Standard
    mock_b.public_access_type = "ObjectRead"  # No es privado

    mock_client.get_bucket.return_value.data = mock_b

    backend = OciStorageBackend.__new__(OciStorageBackend)
    backend.auth_mode = "instance_principal"
    backend.region = "mx-monterrey-1"
    backend.active_auth_mode = "instance_principal"
    backend.is_connected = True
    backend._client = mock_client
    backend._namespace = "test_ns"
    backend._last_error = None

    report = backend.self_check()
    assert report["status"] == "degradado"


def test_status_upload_never_completed_when_put_fails():
    """Si OCI rechaza la subida, put_object nunca reporta status_upload exitoso.

    En producción (sin fallback local permitido) la subida fallida lanza
    RuntimeError en lugar de devolver 'completado'. En desarrollo el backend
    hace fallback explícito a disco local, nunca una subida OCI falsa.
    """
    backend = OciStorageBackend.__new__(OciStorageBackend)
    backend.is_connected = True
    backend._client = MagicMock()
    backend._client.put_object.side_effect = Exception("OCI 500 Internal Error")
    backend._namespace = "test_ns"

    with patch.object(settings, "APP_ENV", "production"), \
         patch.object(settings, "ALLOW_LOCAL_STORAGE", False), \
         patch.object(backend, "head_object", return_value=None):

        with pytest.raises(RuntimeError) as exc_info:
            backend.put_object(
                bucket_name="nuevamente-contenidos-educativos",
                object_name="contenido_test.json",
                data=b'{"data": "test"}',
            )

        assert "OCI 500" in str(exc_info.value)
