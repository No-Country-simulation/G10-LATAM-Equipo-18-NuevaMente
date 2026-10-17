"""
test_storage_queue_endpoints.py

Pruebas unitarias para:
  - Cola persistente de almacenamiento (StorageQueueService y tabla storage_jobs)
  - Endpoints /api/almacenamiento/estado/{content_id} y /api/almacenamiento/reintentar/{content_id}
  - Endpoint /api/salud/servicios con métricas de OCI
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from app.core.config import settings
from app.services.storage_queue_service import StorageQueueService

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_tables():
    queue = StorageQueueService.get_instance()
    queue.init_storage_tables()
    yield


def test_enqueue_content_job_creates_pending_record_with_canonical_key():
    """enqueue_content_job debe registrar el trabajo con clave canónica y estado pendiente."""
    queue = StorageQueueService.get_instance()
    content_id = "test-doc-beginner-123456"
    user_id = "profesor_carlos"

    info = queue.enqueue_content_job(
        content_id=content_id,
        user_id=user_id,
        json_data={"tema": "Redes OCI", "items": [1, 2, 3]},
        version=1,
    )

    assert info["status_upload"] == "pendiente"
    assert "usuarios/profesor_carlos/contenidos/test-doc-beginner-123456/test-doc-beginner-123456_v1.json" == info["objeto_id"]

    # Verificar estado en BD
    status_db = queue.get_content_status(content_id)
    assert status_db["status_upload"] == "pendiente"
    assert status_db["version"] == 1


def test_process_job_transitions_to_completed_on_success():
    """process_job pasa el estado de 'pendiente' a 'completado' cuando el SDK confirma la subida."""
    queue = StorageQueueService.get_instance()
    content_id = "test-success-001"

    info = queue.enqueue_content_job(
        content_id=content_id,
        user_id="usr_01",
        json_data={"test": "data"},
        version=1,
    )

    mock_backend = MagicMock()
    mock_backend.put_object.return_value = {"status_upload": "completado", "sha256": "abc"}

    with patch("app.services.storage_queue_service.get_storage_backend", return_value=mock_backend):
        ok = queue.process_job(info["job_id"])
        assert ok is True

    status_db = queue.get_content_status(content_id)
    assert status_db["status_upload"] == "completado"
    assert status_db["ultimo_error"] is None


def test_process_job_handles_failure_and_retries():
    """process_job incrementa intentos y almacena el último error si el backend falla."""
    queue = StorageQueueService.get_instance()
    content_id = "test-fail-retry"

    info = queue.enqueue_content_job(
        content_id=content_id,
        user_id="usr_02",
        json_data={"test": "data"},
        version=1,
    )

    mock_backend = MagicMock()
    mock_backend.put_object.side_effect = Exception("OCI 503 Service Unavailable")

    with patch("app.services.storage_queue_service.get_storage_backend", return_value=mock_backend):
        ok = queue.process_job(info["job_id"])
        assert ok is False

    status_db = queue.get_content_status(content_id)
    assert status_db["status_upload"] == "pendiente"
    assert status_db["intentos"] == 1
    assert "503" in status_db["ultimo_error"]


def test_endpoint_get_storage_status_found():
    """GET /api/v1/almacenamiento/estado/{content_id} retorna estado 200 con la información."""
    queue = StorageQueueService.get_instance()
    content_id = "test-endpoint-status-123"

    queue.enqueue_content_job(
        content_id=content_id,
        user_id="user_test",
        json_data={"item": 1},
        version=1,
    )

    resp = client.get(f"/api/v1/almacenamiento/estado/{content_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_id"] == content_id
    assert data["status_upload"] == "pendiente"


def test_endpoint_get_storage_status_not_found():
    """GET /api/v1/almacenamiento/estado/{content_id} retorna 404 para un ID inexistente."""
    resp = client.get("/api/v1/almacenamiento/estado/id-inexistente-xyz")
    assert resp.status_code == 404


def test_endpoint_retry_storage_job():
    """POST /api/v1/almacenamiento/reintentar/{content_id} reencola trabajos con error."""
    queue = StorageQueueService.get_instance()
    content_id = "test-retry-endpoint"

    job_info = queue.enqueue_content_job(
        content_id=content_id,
        user_id="user_retry",
        json_data={"key": "val"},
        version=1,
    )

    # Forzar estado error
    from app.core.security import get_db
    conn = get_db()
    conn.execute("UPDATE storage_jobs SET estado = 'error', intentos = 5 WHERE id = ?", (job_info["job_id"],))
    conn.commit()
    conn.close()

    mock_backend = MagicMock()
    mock_backend.put_object.return_value = {"status_upload": "completado"}

    with patch("app.services.storage_queue_service.get_storage_backend", return_value=mock_backend):
        resp = client.post(f"/api/v1/almacenamiento/reintentar/{content_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "exito"


def test_endpoint_salud_servicios_includes_oci_metrics():
    """GET /api/v1/salud/servicios incluye bloque oci_storage con métricas completas."""
    resp = client.get("/api/v1/salud/servicios")
    assert resp.status_code == 200
    data = resp.json()
    assert "oci_storage" in data
    oci_data = data["oci_storage"]
    assert "status" in oci_data
    assert "auth_mode" in oci_data
    assert "trabajos_pendientes" in oci_data
    assert "trabajos_fallidos" in oci_data
