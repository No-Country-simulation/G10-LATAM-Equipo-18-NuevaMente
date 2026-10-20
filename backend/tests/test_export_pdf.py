"""
test_export_pdf.py

Purpose:
    Integration tests for the /export/pdf endpoint.
    Verifies that the generated PDF response has application/pdf content-type
    and begins with the valid PDF magic bytes (%PDF).

Input:
    AdaptedContent payload representing generated educational material.

Output:
    Assertion passes if binary PDF is returned with HTTP 200 and %PDF header.
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_export_pdf_endpoint_success():
    payload = {
        "titulo": "Tutorial de Arquitectura Limpia",
        "introduccion_contextualizada": "Guía práctica para desarrolladores sobre separación de capas y desacoplamiento.",
        "resumen_ejecutivo": "Aprende los principios fundamentales de diseño de software empresarial.",
        "items": [
            {
                "paso": 1,
                "titulo": "Definir las Entidades del Dominio",
                "instruccion": "Crea modelos puros sin dependencias de frameworks externos.",
                "ejemplo": "class User:\n    def __init__(self, id: str, email: str):\n        self.id = id\n        self.email = email",
                "advertencia": "Evita importar ORMs directamente en la capa de dominio."
            },
            {
                "paso": 2,
                "titulo": "Implementar Casos de Uso",
                "instruccion": "Encapsula las reglas de negocio en servicios específicos.",
                "ejemplo": "class RegisterUserUseCase:\n    def execute(self, command):\n        pass"
            }
        ]
    }

    response = client.post("/api/v1/export/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
