import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register_and_login_sqlite():
    import uuid
    unique_email = f"test.anki.{uuid.uuid4().hex[:8]}@empresa.com"
    # Register user
    reg_payload = {
        "name": "Usuario Test Anki",
        "email": unique_email,
        "password": "mi_password_seguro_123"
    }
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "exito"
    assert "access_token" in data
    assert data["user"]["email"] == unique_email

    # Login user
    login_payload = {
        "email": unique_email,
        "password": "mi_password_seguro_123"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["status"] == "exito"
    assert login_data["access_token"] == data["access_token"] or len(login_data["access_token"]) > 20

def test_anki_info_endpoint():
    response = client.get("/api/v1/anki/info")
    assert response.status_code == 200
    data = response.json()
    assert data["requires_api_key"] is False
    assert data["requires_registration"] is False
    assert len(data["features"]) > 0

def test_anki_export_deck_endpoint():
    payload = {
        "deck_name": "Test Mazo Anki",
        "flashcards": [
            {
                "frente": "¿Qué es la repetición espaciada?",
                "dorso": "Es una técnica de aprendizaje donde los repasos se espacian en el tiempo.",
                "pista_didactica": "SuperMemo SM-2 / Anki"
            }
        ]
    }
    response = client.post("/api/v1/anki/export-deck", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/apkg"
    assert len(response.content) > 1000

def test_anki_sync_ankiconnect_endpoint():
    payload = {
        "deck_name": "Test Mazo Anki Sync",
        "flashcards": [
            {
                "frente": "¿Qué es AnkiConnect?",
                "dorso": "Es un complemento local HTTP para Anki Desktop.",
                "pista_didactica": "Puerto 8765"
            }
        ]
    }
    response = client.post("/api/v1/anki/sync-ankiconnect", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["exito", "warning"]
