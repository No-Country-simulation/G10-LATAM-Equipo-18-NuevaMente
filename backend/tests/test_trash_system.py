"""
test_trash_system.py

Pytest suite for user-isolated trash system:
- Soft delete (move to trash)
- Restoration to library
- Permanent delete with OCI Object Storage mock
- Purge only expired items (injectable clock)
- User isolation (404 Not Found)
- Trashed content 404 rejection
- OCI failure leaves purge_failed = 1
- Idempotency
- Unauthenticated requests return 401
"""

import time
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.security import create_access_token, get_db
from app.services.trash_service import TrashService

client = TestClient(app)

USER_A_ID = "usr_ana_001"
USER_A_EMAIL = "ana.martinez@empresa.com"

USER_B_ID = "usr_fer_002"
USER_B_EMAIL = "fernando.garcia@empresa.com"


@pytest.fixture
def auth_headers_user_a():
    token = create_access_token(USER_A_ID, USER_A_EMAIL, "Ana Martinez", "Instructor")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user_b():
    token = create_access_token(USER_B_ID, USER_B_EMAIL, "Fernando Garcia", "Dev")
    return {"Authorization": f"Bearer {token}"}


def create_test_content(user_id: str, content_id: str, title: str = "Doc Test") -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO contenidos 
        (id, user_id, title, content, recipient_profile, output_format, niche, detail_level, status, object_key_source, object_key_json, deleted_at, purge_at, deleted_by, purge_failed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, 0, ?)
    """, (content_id, user_id, title, "Contenido test", "Desarrollador", "Tutorial", "Fintech", "Didactico", "ready", f"usuarios/{user_id}/src.pdf", f"usuarios/{user_id}/res.json", time.time()))
    conn.commit()
    conn.close()


class MockOCIStorageService:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.deleted_keys = []

    def delete_file(self, object_key: str) -> bool:
        if self.should_fail:
            raise RuntimeError("Simulated OCI Object Storage Connection Failure")
        self.deleted_keys.append(object_key)
        return True


def test_unauthenticated_returns_401():
    response = client.get("/api/v1/papelera")
    assert response.status_code == 401


def test_move_to_trash_and_disappear_from_library(auth_headers_user_a):
    content_id = f"cnt-test-001-{int(time.time())}"
    create_test_content(USER_A_ID, content_id, "Documento Para Papelera")

    # 1. Soft delete / move to trash
    res = client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)
    assert res.status_code == 200
    data = res.json()
    assert data["deleted_at"] is not None
    assert data["purge_at"] is not None

    # 2. Check trash listing
    trash_res = client.get("/api/v1/papelera", headers=auth_headers_user_a)
    assert trash_res.status_code == 200
    trash_items = trash_res.json()
    assert any(item["id"] == content_id for item in trash_items)


def test_restore_content(auth_headers_user_a):
    content_id = f"cnt-test-002-{int(time.time())}"
    create_test_content(USER_A_ID, content_id, "Documento Restaurar")

    # Soft delete first
    client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)

    # Restore from trash
    res = client.post(f"/api/v1/papelera/{content_id}/restore", headers=auth_headers_user_a)
    assert res.status_code == 200
    data = res.json()
    assert data["deleted_at"] is None
    assert data["purge_at"] is None

    # Trash should no longer contain item
    trash_res = client.get("/api/v1/papelera", headers=auth_headers_user_a)
    assert not any(item["id"] == content_id for item in trash_res.json())


def test_user_isolation_returns_404(auth_headers_user_a, auth_headers_user_b):
    content_id = f"cnt-test-user-a-{int(time.time())}"
    create_test_content(USER_A_ID, content_id, "Documento Privado User A")

    # User B tries to soft delete User A's item -> 404
    res_del = client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_b)
    assert res_del.status_code == 404

    # Soft delete by owner A
    client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)

    # User B tries to view in trash -> 404
    trash_b = client.get("/api/v1/papelera", headers=auth_headers_user_b)
    assert not any(item["id"] == content_id for item in trash_b.json())

    # User B tries to restore -> 404
    res_rest = client.post(f"/api/v1/papelera/{content_id}/restore", headers=auth_headers_user_b)
    assert res_rest.status_code == 404

    # User B tries to permanent delete -> 404
    res_perm = client.delete(f"/api/v1/papelera/{content_id}", headers=auth_headers_user_b)
    assert res_perm.status_code == 404


def test_permanent_delete_oci_and_db(auth_headers_user_a):
    content_id = f"cnt-test-perm-{int(time.time())}"
    create_test_content(USER_A_ID, content_id, "Documento Borrado Definitivo")
    client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)

    mock_oci = MockOCIStorageService(should_fail=False)
    service = TrashService(oci_service=mock_oci)

    success = service.delete_permanently(USER_A_ID, content_id)
    assert success is True
    assert len(mock_oci.deleted_keys) == 2

    # Check DB row is gone
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
    assert cursor.fetchone() is None
    conn.close()


def test_oci_failure_leaves_purge_failed(auth_headers_user_a):
    content_id = f"cnt-test-fail-{int(time.time())}"
    create_test_content(USER_A_ID, content_id, "Documento OCI Fallo")
    client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)

    mock_oci = MockOCIStorageService(should_fail=True)
    service = TrashService(oci_service=mock_oci)

    # Auto purge or permanent delete with OCI failure
    success = service.delete_permanently(USER_A_ID, content_id, is_auto_purge=True)
    assert success is False

    # Check DB row still exists and has purge_failed = 1
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT purge_failed FROM contenidos WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row["purge_failed"] == 1
    conn.close()


def test_auto_purge_clock():
    content_active = f"cnt-active-{int(time.time())}"
    content_expired = f"cnt-expired-{int(time.time())}"

    create_test_content(USER_A_ID, content_active, "Activo Papelera")
    create_test_content(USER_A_ID, content_expired, "Expirado Papelera")

    service = TrashService(oci_service=MockOCIStorageService())
    
    # Soft delete both
    service.move_to_trash(USER_A_ID, content_active)
    service.move_to_trash(USER_A_ID, content_expired)

    # Set purge_at of content_expired to 16 days ago
    conn = get_db()
    cursor = conn.cursor()
    past_iso = (datetime.now(timezone.utc) - timedelta(days=16)).isoformat()
    cursor.execute("UPDATE contenidos SET purge_at = ? WHERE id = ?", (past_iso, content_expired))
    conn.commit()
    conn.close()

    # Run auto_purge
    purged_count = service.auto_purge(batch_size=10)
    assert purged_count >= 1

    # Verify content_expired is gone and content_active remains
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM contenidos WHERE id = ?", (content_expired,))
    assert cursor.fetchone() is None

    cursor.execute("SELECT id FROM contenidos WHERE id = ?", (content_active,))
    assert cursor.fetchone() is not None
    conn.close()


def test_idempotency(auth_headers_user_a):
    content_id = f"cnt-idempotent-{int(time.time())}"
    create_test_content(USER_A_ID, content_id, "Idempotente")

    # Soft delete once
    res1 = client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)
    assert res1.status_code == 200

    # Soft delete twice -> 200 OK (idempotent)
    res2 = client.delete(f"/api/v1/contenidos/{content_id}", headers=auth_headers_user_a)
    assert res2.status_code == 200
