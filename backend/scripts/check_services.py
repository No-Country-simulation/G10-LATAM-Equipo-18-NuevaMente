"""
check_services.py

Script de diagnóstico y estado de servicios para NuevaMente Backend.
Verifica la disponibilidad de componentes clave (Python, LLM Gemini, Embeddings,
Groq, Jina, paquetes de extracción/NLP) SIN exponer ninguna clave o secreto.

Uso:
    python backend/scripts/check_services.py
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Tuple

import os
import sys
import time
import logging
from typing import Dict, Any, Tuple

# Load environment variables from backend/.env or .env
try:
    from dotenv import load_dotenv
    backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    else:
        load_dotenv()
except ImportError:
    pass

# Inserción de ruta raíz del backend para importaciones relativas si es necesario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuración básica de logging
logging.basicConfig(level=logging.ERROR)

def get_python_info() -> Dict[str, str]:
    """Retorna información sobre la versión de Python."""
    version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return {
        "version": version_str,
        "platform": sys.platform
    }

def get_keys_status() -> Dict[str, Any]:
    """
    Comprueba la presencia de variables de entorno de claves API.
    NUNCA retorna ni imprime el valor de las claves.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEY", "")
    jina_key = os.getenv("JINA_API_KEY", "")

    has_gemini = bool(gemini_key and gemini_key != "MOCK_GEMINI_KEY")
    has_groq = bool(groq_key and groq_key != "MOCK_GROQ_KEY")
    has_jina = bool(jina_key and jina_key != "MOCK_JINA_KEY")

    # Verificación de formato Gemini (AIza o AQ.)
    gemini_format_valid = "no"
    if has_gemini:
        if gemini_key.startswith("AIza") or gemini_key.startswith("AQ."):
            gemini_format_valid = "sí"

    return {
        "gemini_presente": has_gemini,
        "gemini_formato_aiza_o_aq": gemini_format_valid,
        "groq_presente": has_groq,
        "jina_presente": has_jina,
    }

def test_llm_gemini() -> Dict[str, Any]:
    """
    Prueba real mínima al LLM de Gemini con prompt 'Responde solo: ok'.
    Traduce errores según códigos HTTP/excepciones conocidas.
    """
    from app.core.config import settings
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "MOCK_GEMINI_KEY":
        return {
            "status": "error",
            "message": "GEMINI_API_KEY ausente o no configurada",
            "latency_ms": 0,
            "raw_response": None
        }

    start_time = time.time()
    try:
        import httpx
        from google import genai
        from google.genai import types

        # Timeout estricto para evitar bloqueos
        httpx_client = httpx.Client(timeout=10.0)
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(httpx_client=httpx_client)
        )
        
        response = client.models.generate_content(
            model=settings.DEFAULT_GEMINI_MODEL_FLASH,
            contents=["Responde solo: ok"],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        resp_text = (response.text or "").strip()

        return {
            "status": "ok",
            "message": "LLM Gemini responde correctamente",
            "latency_ms": elapsed_ms,
            "raw_response": resp_text
        }
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        exc_str = str(exc)
        
        # Traducción de errores según reglas de negocio
        if "401" in exc_str or "403" in exc_str or "UNAUTHENTICATED" in exc_str or "PERMISSION_DENIED" in exc_str or "API_KEY_INVALID" in exc_str:
            translated = "clave inválida, de otro servicio o API no habilitada"
        elif "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str or "QUOTA" in exc_str:
            translated = "cuota excedida (HTTP 429)"
        elif "500" in exc_str or "503" in exc_str or "CONNECT" in exc_str or "SSL" in exc_str or "CERTIFICATE" in exc_str or "Timeout" in exc_str:
            translated = "error de conectividad (red / SSL / timeout)"
        else:
            translated = f"error en llamada a Gemini: {exc_str[:100]}"

        return {
            "status": "error",
            "message": translated,
            "latency_ms": elapsed_ms,
            "raw_response": None
        }

def test_embeddings() -> Dict[str, Any]:
    """
    Prueba real mínima de embeddings (2 frases).
    Verifica dimensión, latencia y proveedor utilizado.
    """
    start_time = time.time()
    try:
        from app.services.embedding_service import EmbeddingService
        
        service = EmbeddingService()
        test_texts = ["Hola mundo", "Prueba de adaptacion educativa"]
        vectors = service.embed_batch(test_texts)
        model_name = service.model_name
        
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        
        if vectors and len(vectors) == 2:
            dim = len(vectors[0])
            return {
                "status": "ok",
                "message": f"Embeddings funcionales con proveedor {model_name}",
                "dimension": dim,
                "latency_ms": elapsed_ms,
                "model_name": model_name
            }
        else:
            return {
                "status": "error",
                "message": "No se obtuvieron vectores de la prueba de embeddings",
                "dimension": 0,
                "latency_ms": elapsed_ms,
                "model_name": None
            }
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        exc_str = str(exc)
        return {
            "status": "error",
            "message": f"Fallo en servicio de embeddings: {exc_str[:120]}",
            "dimension": 0,
            "latency_ms": elapsed_ms,
            "model_name": None
        }

def test_optional_services() -> Dict[str, Any]:
    """Verifica servicios opcionales Jina y Groq si hay clave presente."""
    keys = get_keys_status()
    
    jina_status = "Desactivado (sin clave)"
    if keys["jina_presente"]:
        try:
            from app.infrastructure.jina_client import JinaClient
            client = JinaClient()
            vecs = client.embed(["test"], task="retrieval.passage")
            if vecs:
                jina_status = "OK (disponible)"
            else:
                jina_status = "Error al generar vector"
        except Exception as exc:
            jina_status = f"Error: {str(exc)[:60]}"
            
    groq_status = "Desactivado (sin clave)"
    if keys["groq_presente"]:
        try:
            from app.infrastructure.groq_client import GroqClient
            client = GroqClient()
            if client.has_real_key:
                groq_status = "OK (configurado)"
            else:
                groq_status = "Error en configuración"
        except Exception as exc:
            groq_status = f"Error: {str(exc)[:60]}"

    return {
        "jina": jina_status,
        "groq": groq_status
    }

def get_package_versions() -> Dict[str, str]:
    """Comprueba la disponibilidad y versión de las librerías indicadas."""
    packages = ["pymupdf", "pymupdf4llm", "pypdf", "sentence_transformers", "torch"]
    results = {}
    
    for pkg in packages:
        try:
            if pkg == "pymupdf":
                import fitz
                results[pkg] = fitz.__version__
            elif pkg == "pymupdf4llm":
                import pymupdf4llm
                results[pkg] = getattr(pymupdf4llm, "__version__", "disponible")
            elif pkg == "pypdf":
                import pypdf
                results[pkg] = getattr(pypdf, "__version__", "disponible")
            elif pkg == "sentence_transformers":
                import sentence_transformers
                results[pkg] = getattr(sentence_transformers, "__version__", "disponible")
            elif pkg == "torch":
                import torch
                results[pkg] = getattr(torch, "__version__", "disponible")
        except ImportError:
            results[pkg] = "No disponible"
        except Exception as exc:
            results[pkg] = f"Error de carga: {str(exc)[:40]}"
            
    return results

def check_all_services() -> Dict[str, Any]:
    """
    Función integradora reutilizable para el endpoint /api/salud/servicios
    o consumo programático.
    """
    python_info = get_python_info()
    keys_info = get_keys_status()
    llm_info = test_llm_gemini()
    emb_info = test_embeddings()
    opt_info = test_optional_services()
    pkg_info = get_package_versions()
    
    is_healthy = (llm_info["status"] == "ok") and (emb_info["status"] == "ok")
    
    return {
        "is_healthy": is_healthy,
        "python": python_info,
        "keys": keys_info,
        "llm_gemini": llm_info,
        "embeddings": emb_info,
        "opcionales": opt_info,
        "paquetes": pkg_info
    }

def print_health_table(report: Dict[str, Any]):
    """Imprime una tabla Markdown limpia en stdout (SIN SECRETOS)."""
    print("\n" + "="*80)
    print("               DIAGNÓSTICO DE SALUD DE SERVICIOS - NUEVAMENTE")
    print("="*80 + "\n")
    
    print(f"**Python:** {report['python']['version']} ({report['python']['platform']})\n")
    
    print("| Componente | Indicador / Estado | Detalle / Latencia |")
    print("|---|---|---|")
    
    keys = report["keys"]
    print(f"| GEMINI_API_KEY presente | `{keys['gemini_presente']}` | Formato AIza/AQ.: `{keys['gemini_formato_aiza_o_aq']}` |")
    print(f"| GROQ_API_KEY presente | `{keys['groq_presente']}` | - |")
    print(f"| JINA_API_KEY presente | `{keys['jina_presente']}` | - |")
    
    llm = report["llm_gemini"]
    llm_status = "SUCCESS" if llm["status"] == "ok" else "FAIL"
    print(f"| LLM Gemini (`gemini-2.5-flash`) | **{llm_status}** | {llm['message']} ({llm['latency_ms']} ms) |")
    
    emb = report["embeddings"]
    emb_status = "SUCCESS" if emb["status"] == "ok" else "FAIL"
    emb_detail = f"{emb['message']} | Dim: {emb['dimension']} ({emb['latency_ms']} ms)"
    print(f"| Embeddings principales | **{emb_status}** | {emb_detail} |")
    
    opt = report["opcionales"]
    print(f"| Jina AI Embeddings | {opt['jina']} | Respaldo en cascada |")
    print(f"| Groq LLM | {opt['groq']} | Respaldo opcional |")
    
    pkgs = report["paquetes"]
    print(f"| Library: pymupdf | {pkgs['pymupdf']} | Extractor PDF |")
    print(f"| Library: pymupdf4llm | {pkgs['pymupdf4llm']} | Extractor Markdown PDF |")
    print(f"| Library: pypdf | {pkgs['pypdf']} | Extractor respaldo |")
    print(f"| Library: sentence_transformers | {pkgs['sentence_transformers']} | Embeddings locales |")
    print(f"| Library: torch | {pkgs['torch']} | Motor ML |")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    report = check_all_services()
    print_health_table(report)
    
    if not report["is_healthy"]:
        print("CRITICAL: El LLM de Gemini o los Embeddings principales fallaron.")
        sys.exit(1)
    else:
        print("SALUD OK: Todos los servicios principales responden adecuadamente.")
        sys.exit(0)
