"""
test_tutorial_step_formatting.py

Purpose:
    Regression tests verifying that tutorial steps:
    1. Are ordered sequentially 1..N (fixing disjoint/random order e.g. 1, 7, 22, 4, 5).
    2. Do not contain duplicate prefixes like 'Paso X:' in the title.
    3. Do not leak raw markdown artifacts (# **VII.**) or page numbering footers (53 de 363).
"""

import pytest
from app.schemas.adaptation import AdaptationRequest
from app.services.pipeline_stages import PipelineStages, _clean_concept_text


def test_clean_concept_text_filters_noise():
    # Markdown symbols with Roman numerals
    res = _clean_concept_text("# **VII.**", context="Configuración de balanceadores de carga en la nube.", doc_title="Manual Cloud")
    assert "VII" not in res
    assert "#" not in res
    assert "*" not in res
    assert len(res) > 3

    # PDF page numbers
    res_page = _clean_concept_text("53 de 363", context="Monitoreo de métricas y alertas del sistema operativo.", doc_title="Guía Linux")
    assert "53 de 363" not in res_page
    assert len(res_page) > 3

    # Trailing PDF xref / binary artifacts
    res_xref = _clean_concept_text("startxref 542918 %%EOF", context="Despliegue automatizado con contenedores Docker.", doc_title="DevOps")
    assert "startxref" not in res_xref
    assert "%%EOF" not in res_xref

    # Clean concept keeps valid technical text
    res_valid = _clean_concept_text("Arquitectura de Microservicios", context="", doc_title="")
    assert res_valid == "Arquitectura de Microservicios"


def test_tutorial_sequential_reindexing_and_deduplication():
    stages = PipelineStages()
    request = AdaptationRequest(
        output_format="tutorial",
        niche="Tecnología",
        recipient_profile="Desarrollador Junior",
        documento_titulo="Manual de Infraestructura Cloud",
        documento_contenido="Contenido sobre infraestructura cloud, balanceadores de carga y contenedores Docker.",
    )

    # Disordered items with duplicate 'Paso X:' in title and noisy titles
    disordered_items = [
        {
            "paso": 1,
            "titulo": "Paso 1: Configuración y aplicación de # **VII.**",
            "instruccion": "Implementar directrices técnicas.",
            "ejemplo": "deploy()",
        },
        {
            "paso": 7,
            "titulo": "Paso 7: Configuración y aplicación de 53 de 363",
            "instruccion": "Configurar balanceador de carga.",
            "ejemplo": "setup_lb()",
        },
        {
            "paso": 22,
            "titulo": "Paso 22: Paso 22: Configuración y aplicación de 88 de 363",
            "instruccion": "Verificar certificados SSL.",
            "ejemplo": "check_ssl()",
        },
        {
            "paso": 4,
            "titulo": "Step 4: Configuración de seguridad perimetral",
            "instruccion": "Aplicar firewall rules.",
            "ejemplo": "ufw enable",
        },
        {
            "paso": 5,
            "titulo": "Configuración y aplicación de 308 de 363",
            "instruccion": "Habilitar registros de auditoría.",
            "ejemplo": "auditd start",
        },
    ]

    adapted = stages._format_adapted_content(
        request=request,
        doc_title="Manual de Infraestructura Cloud",
        items=disordered_items,
        effective_count=len(disordered_items),
        target_language="Spanish",
    )

    # Verify strict 1-based sequential ordering
    step_numbers = [it["paso"] for it in adapted.items]
    assert step_numbers == [1, 2, 3, 4, 5], f"Expected [1, 2, 3, 4, 5], got {step_numbers}"

    # Verify no title contains 'Paso X:' or 'Step X:' prefix
    for idx, it in enumerate(adapted.items):
        title = it["titulo"]
        assert not title.lower().startswith("paso "), f"Item {idx+1} title should not start with 'Paso ': '{title}'"
        assert not title.lower().startswith("step "), f"Item {idx+1} title should not start with 'Step ': '{title}'"
        assert "#" not in title, f"Item {idx+1} title has markdown '#': '{title}'"
        assert "*" not in title, f"Item {idx+1} title has markdown '*': '{title}'"
        assert "de 363" not in title, f"Item {idx+1} title contains leaked page number: '{title}'"

    # Verify tutorial sections have clean sequential encabezado
    assert len(adapted.tutorial_sections) == 5
    for idx, sec in enumerate(adapted.tutorial_sections):
        expected_prefix = f"Paso {idx + 1}:"
        assert sec["encabezado"].startswith(expected_prefix), f"Section {idx+1} heading should start with '{expected_prefix}', got '{sec['encabezado']}'"
        # Ensure no double prefix like 'Paso 1: Paso 1:'
        after_prefix = sec["encabezado"][len(expected_prefix):].strip()
        assert not after_prefix.lower().startswith("paso "), f"Double prefix detected in section {idx+1}: '{sec['encabezado']}'"
