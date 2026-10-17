"""
test_multiformat_export.py

Purpose:
    Unit tests for ExportService and Multiformat Export endpoints:
    1. Markdown export (.md)
    2. Anki-compatible CSV deck (.csv)
    3. Formatted Didactic PDF (.pdf)
"""

import pytest
from app.services.export_service import ExportService, slugify_title
from app.services.pdf_export_service import PDFExportService


@pytest.fixture
def sample_payload():
    return {
        "contenido_adaptado": {
            "titulo": "Arquitectura de Microservicios en OCI",
            "introduccion_contextualizada": "Guía práctica para desplegar microservicios escalables en Oracle Cloud.",
            "resumen_ejecutivo": "Puntos clave sobre contenedores, balanceo de carga y alta disponibilidad.",
            "secciones_tutorial": [
                {
                    "encabezado": "Paso 1: Configuración de VCN",
                    "contenido": "Crear la red virtual con subredes privadas y públicas.",
                },
                {
                    "encabezado": "Paso 2: Despliegue en Kubernetes",
                    "contenido": "Aplicar manifiestos con kubectl apply -f deployment.yaml.",
                },
            ],
            "items": [
                {
                    "paso": 1,
                    "titulo": "Configuración de VCN",
                    "instruccion": "Crear la red virtual con subredes privadas y públicas.",
                    "ejemplo": "oci network vcn create --cidr-block 10.0.0.0/16",
                    "fuentes": [{"chunk_id": "chunk_01", "seccion": "Redes VCN", "pagina": 12}],
                },
                {
                    "paso": 2,
                    "titulo": "Despliegue en Kubernetes",
                    "instruccion": "Aplicar manifiestos con kubectl apply -f deployment.yaml.",
                    "ejemplo": "kubectl apply -f deployment.yaml",
                    "fuentes": [{"chunk_id": "chunk_02", "seccion": "OKE Cluster", "pagina": 45}],
                },
            ],
        },
        "metadatos": {
            "perfil_aplicado": "Desarrollador Junior",
            "formato_generado": "Tutorial Paso a Paso",
            "tiempo_estimado_estudio_minutos": 20,
        },
        "evaluacion_calidad": {
            "anclaje_fuente_score": 0.95,
            "claridad_pedagogica": "Alta",
            "observaciones": "Comandos CLI verificados con documentación oficial de Oracle.",
        },
        "almacenamiento_oci": {
            "bucket": "nuevamente-contenidos-educativos",
            "objeto_id": "usuarios/anonimo/contenidos/manual_v1.json",
        },
    }


def test_slugify_title():
    assert slugify_title("Arquitectura de Microservicios en OCI!") == "arquitectura-de-microservicios-en-oci"
    assert slugify_title("Guía Paso a Paso 2026") == "guia-paso-a-paso-2026"
    assert slugify_title("") == "nuevamente-contenido"


def test_export_to_markdown(sample_payload):
    service = ExportService()
    md = service.export_to_markdown(sample_payload)

    assert "# 🎓 Arquitectura de Microservicios en OCI" in md
    assert "Desarrollador Junior" in md
    assert "Tutorial Paso a Paso" in md
    assert "95%" in md
    assert "Paso 1: Configuración de VCN" in md
    assert "oci network vcn create" in md
    assert "Redes VCN" in md


def test_export_to_anki_csv(sample_payload):
    service = ExportService()
    csv_text = service.export_to_anki_csv(sample_payload)

    assert "#separator:tab" in csv_text
    assert "#html:true" in csv_text
    assert "#tags column:3" in csv_text
    assert "PASO 1" in csv_text
    assert "Configuración de VCN" in csv_text
    assert "NuevaMente::Tutorial_Paso_a_Paso" in csv_text


def test_export_to_pdf_bytes(sample_payload):
    service = ExportService()
    pdf_bytes = service.export_to_pdf_bytes(sample_payload)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")
