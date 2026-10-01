"""
test_phase0_health.py

Pruebas unitarias de la Fase 0 (Higiene de secretos y salud del entorno).
"""

import os
import sys
import pytest

# Inserción de ruta backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.check_services import get_keys_status, get_python_info, get_package_versions

def test_env_example_has_no_secret_values():
    """Verifica que .env.example no tenga claves reales ni valores quemados."""
    env_example_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env.example"))
    assert os.path.exists(env_example_path), ".env.example debe existir"
    
    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            # GEMINI_API_KEY, GROQ_API_KEY, JINA_API_KEY no deben contener valores
            if key in ["GEMINI_API_KEY", "GROQ_API_KEY", "JINA_API_KEY"]:
                assert val == "", f"{key} en .env.example no debe contener ningún valor"

def test_get_keys_status_no_secrets_exposed():
    """Garantiza que get_keys_status devuelva solo booleanos e indicadores de formato."""
    status = get_keys_status()
    assert "gemini_presente" in status
    assert isinstance(status["gemini_presente"], bool)
    assert status["gemini_formato_aiza_o_aq"] in ["sí", "no"]
    assert isinstance(status["groq_presente"], bool)
    assert isinstance(status["jina_presente"], bool)

def test_python_and_packages_info():
    """Comprueba obtención de versiones sin fallas."""
    py_info = get_python_info()
    assert "version" in py_info
    
    pkgs = get_package_versions()
    assert "pymupdf" in pkgs
    assert "pymupdf4llm" in pkgs
    assert "pypdf" in pkgs
    assert "sentence_transformers" in pkgs
    assert "torch" in pkgs
