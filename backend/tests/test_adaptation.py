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

def test_adapt_content_endpoint():
    payload = {
        "documento_titulo": "Introduccion a la Arquitectura de Redes VCN en OCI",
        "documento_contenido": "La Virtual Cloud Network (VCN) es una red privada y personalizable configurada en Oracle Cloud Infrastructure.",
        "perfil_destinatario": "Principiante",
        "formato_salida": "Flashcards",
        "nicho_sector": "General",
        "nivel_detalle": "Didactico"
    }
    
    response = client.post("/api/v1/adapt-content", json=payload)
    if response.status_code != 200:
        print("Response error:", response.status_code, response.text)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "exito"
    assert "metadatos" in data
    assert "contenido_adaptado" in data
    assert "evaluacion_calidad" in data
    assert "almacenamiento_oci" in data
    assert data["evaluacion_calidad"]["anclaje_fuente_score"] >= 0.90

def test_auth_login_endpoint():
    payload = {
        "email": "ana.martinez@empresa.com",
        "password": "password123",
        "name": "Ana Martínez"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "exito"
    assert data["user"]["name"] == "Ana Martínez"
    assert data["user"]["isLoggedIn"] is True

def test_auth_register_endpoint():
    payload = {
        "name": "Fernando García",
        "email": "fernando.garcia@empresa.com",
        "password": "securepassword"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "exito"
    assert data["user"]["name"] == "Fernando García"
    assert data["user"]["isLoggedIn"] is True

if __name__ == "__main__":
    print("Testing health check...")
    test_health_check()
    print("✓ Health check passed.")

    print("Testing adapt content endpoint (backward compatibility)...")
    test_adapt_content_endpoint()
    print("✓ Adapt content endpoint passed successfully!")

    print("Testing auth login endpoint...")
    test_auth_login_endpoint()
    print("✓ Auth login endpoint passed successfully!")

    print("Testing auth register endpoint...")
    test_auth_register_endpoint()
    print("✓ Auth register endpoint passed successfully!")
