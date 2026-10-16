import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add backend directory to sys.path so app modules can be imported
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# NOTE: the former /adapt-content endpoint was removed in favor of the real
# two-step flow (POST /documents, then POST /documents/{id}/adapt). Its tests
# were integration-style and required live LLM/embedding keys, so they were
# dropped together with the endpoint.

def test_auth_login_endpoint():
    payload = {
        "email": "ana.martinez@empresa.com",
        "password": "password123",
        "name": "Ana Martinez"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "exito"
    assert data["user"]["name"] == "Ana Martinez"

def test_auth_register_endpoint():
    import uuid
    unique_email = f"user_{uuid.uuid4().hex[:8]}@empresa.com"
    payload = {
        "name": "Nuevo Usuario Test",
        "email": unique_email,
        "password": "securepassword123"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "exito"
    assert data["user"]["name"] == "Nuevo Usuario Test"

if __name__ == "__main__":
    print("Testing health check...")
    test_health_check()
    print("✓ Health check passed.")

    print("Testing auth login endpoint...")
    test_auth_login_endpoint()
    print("✓ Auth login endpoint passed successfully!")

    print("Testing auth register endpoint...")
    test_auth_register_endpoint()
    print("✓ Auth register endpoint passed successfully!")
