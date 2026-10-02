"""
gemini_client.py

Purpose:
    Thin wrapper around the Google Gemini SDK (google-genai v2.x) for
    text generation. Falls back to a structured mock response when no
    valid API key is present (development / CI mode).

Input:
    GEMINI_API_KEY environment variable.
    prompt (str), optional system_instruction (str), model_name (str).

Output:
    Generated text (str), or a JSON mock string in fallback mode.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger("GeminiClient")


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.has_real_key = bool(self.api_key and self.api_key != "MOCK_GEMINI_KEY")
        self._client = None

        if self.has_real_key:
            try:
                import httpx  # noqa: PLC0415
                from google import genai  # noqa: PLC0415
                from google.genai import types  # noqa: PLC0415

                # Bypass SSL verification on Windows if local CA certificates fail
                httpx_client = httpx.Client(verify=False)
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(httpx_client=httpx_client)
                )
                logger.info("Google Gemini SDK (google-genai v2) configured successfully with SSL bypass.")
            except Exception as exc:
                logger.warning("Failed to initialize Gemini SDK: %s. Using mock mode.", exc)
                self.has_real_key = False
        else:
            logger.info("Gemini mock mode active (no valid API key).")

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        json_output: bool = True,
        image_path: Optional[str] = None,
    ) -> str:
        model_name = model_name or os.getenv("GEMINI_LLM_MODEL", "gemini-flash-latest")
        """
        Generates content using Gemini. Supports multimodal input if image_path is provided.
        Falls back to mock on any error.
        """
        if self.has_real_key and self._client is not None:
            try:
                from google.genai import types  # noqa: PLC0415
                from PIL import Image # noqa: PLC0415

                config_kwargs = {}
                if json_output:
                    config_kwargs["response_mime_type"] = "application/json"
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                contents = [prompt]
                if image_path and os.path.exists(image_path):
                    img = Image.open(image_path)
                    contents.append(img)

                response = self._client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
                )
                return response.text
            except Exception as exc:
                logger.warning("Gemini API call failed: %s.", exc)
                raise RuntimeError(f"Fallo en llamada a la API de Gemini: {exc}") from exc

        allow_demo = os.getenv("ALLOW_DEMO_CONTENT", "false").lower() == "true"
        if allow_demo:
            return self._mock_response(prompt)
            
        raise RuntimeError("GEMINI_API_KEY no configurada o inválida. Configura tu API key en backend/.env.")

    def _mock_response(self, prompt: str) -> str:
        """Returns a rich, structured JSON string for development / no-key / fallback environments."""
        import re  # noqa: PLC0415
        
        topic_match = re.search(r"Tema/Nicho:\s*'([^']+)'", prompt)
        topic = topic_match.group(1) if topic_match else "Documento Técnico"
        if not topic or topic == "None":
            topic = "Documento Técnico"

        profile_match = re.search(r"perfil:\s*'([^']+)'", prompt)
        profile = profile_match.group(1) if profile_match else "General"

        format_match = re.search(r"Formato de salida requerido:\s*'([^']+)'", prompt)
        output_fmt = format_match.group(1) if format_match else "Guía Práctica Paso a Paso (Tutorial)"

        passages = re.findall(r"Fragmento \d+:\s*([^\n]+)", prompt)
        first_fact = passages[0] if passages else f"Análisis de los conceptos clave y estructura de {topic}."

        fmt = prompt.lower()
        is_flashcards = "flashcard" in fmt
        is_quiz = "quiz" in fmt
        is_tldr = "tldr" in fmt or "resumen" in fmt

        items = []
        quizzes = []
        secciones_tutorial = []
        resumen_ejecutivo = None

        if is_flashcards:
            items = [
                {
                    "frente": f"¿Cuál es el principio fundamental de {topic}?",
                    "dorso": f"{first_fact[:180]}...",
                    "pista_didactica": f"Relaciona este concepto con las mejores prácticas para {profile}."
                },
                {
                    "frente": f"¿Cómo se implementa {topic} en producción?",
                    "dorso": f"Siguiendo los estándares técnicos y la estructura especificada en el documento original.",
                    "pista_didactica": "Verifica los prerequisitos del módulo."
                }
            ]
        elif is_quiz:
            quizzes = [
                {
                    "pregunta": f"¿Cuál es el propósito principal de {topic}?",
                    "opciones": [
                        f"{first_fact[:100]}...",
                        "Desactivar las validaciones de seguridad en el sistema",
                        "Ignorar los requerimientos de la arquitectura original",
                        "Eliminar el control de excepciones y logs"
                    ],
                    "respuesta_correcta": f"{first_fact[:100]}...",
                    "justificacion_didactica": f"Basado en la documentación técnica de {topic}, este principio garantiza el correcto funcionamiento."
                }
            ]
        elif is_tldr:
            resumen_ejecutivo = f"RESUMEN EJECUTIVO (TL;DR) DE {topic.upper()}:\n\n1. Concepto Principal: {first_fact[:150]}\n2. Perfil Objetivo: Diseñado para {profile}.\n3. Aplicación Práctica: Integración de estándares didácticos."
            secciones_tutorial = [
                {
                    "encabezado": f"1. Síntesis Inicial de {topic}",
                    "contenido": f"{first_fact}. Este resumen condensa las premisas fundamentales del documento para una asimilación rápida por parte de {profile}."
                },
                {
                    "encabezado": "2. Puntos Clave y Recomendaciones",
                    "contenido": f"Para aplicar adecuadamente {topic}, se recomienda seguir una estructura iterativa de aprendizaje basada en evidencia."
                }
            ]
        else:
            # Default Tutorial / Guía Paso a Paso
            secciones_tutorial = [
                {
                    "encabezado": f"Paso 1: Introducción a {topic}",
                    "contenido": f"Bienvenido a la guía adaptada de **{topic}**. En esta sección se abordan los conceptos iniciales: {first_fact[:200]}.\n\n```mermaid\ngraph TD\n    A[📥 Ingestión de {topic}] --> B[⚙️ Procesamiento Didáctico]\n    B --> C[🎯 Aplicación para {profile}]\n```\n\n| Fase Didáctica | Objetivo | Estado |\n| --- | --- | --- |\n| 1. Diagnóstico | Evaluar {topic} | Completado |\n| 2. Ejecución | Adaptación para {profile} | Validado |\n"
                },
                {
                    "encabezado": f"Paso 2: Profundización Técnica en {topic}",
                    "contenido": f"Se analizan las reglas de negocio y patrones contenidos en la documentación de {topic}, ajustados al perfil de {profile}."
                },
                {
                    "encabezado": "Paso 3: Verificación y Caso Práctico",
                    "contenido": f"Validación de los aprendizajes adquiridos sobre {topic} mediante ejemplos y comprobación de fidelidad RAG."
                }
            ]

        return json.dumps({
            "metadatos": {
                "perfil_aplicado": profile,
                "formato_generado": output_fmt,
                "tiempo_estimado_estudio_minutos": 10,
                "conceptos_clave": [topic, "Principios Técnicos", "Buenas Prácticas", "Verificación"],
                "prerrequisitos": ["Conocimientos Previos"]
            },
            "contenido_adaptado": {
                "titulo": f"Guía Adaptada de {topic} para {profile}",
                "introduccion_contextualizada": f"Esta guía adaptada transforma la documentación técnica de '{topic}' en un marco práctico orientado al perfil de {profile}.",
                "resumen_ejecutivo": resumen_ejecutivo,
                "items": items,
                "quizzes": quizzes,
                "secciones_tutorial": secciones_tutorial
            },
            "evaluacion_calidad": {
                "anclaje_fuente_score": 0.98,
                "claridad_pedagogica": "Alta",
                "observaciones": f"Adaptación generada y validada contra el documento original '{topic}'."
            }
        })
