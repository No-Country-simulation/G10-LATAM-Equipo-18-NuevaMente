import os
import json
import logging
from typing import Optional, Dict, Any

from app.infrastructure.gemini_client import GeminiClient

logger = logging.getLogger("PdfParserService")

class PdfParserService:
    """
    Servicio avanzado de parsing de documentos PDF impulsado por IA LLM (Gemini Vision)
    y pymupdf4llm para convertir manuales técnicos densos en Markdown estructurado,
    preservando tablas, diagramas y jerarquías de código.
    """
    def __init__(self):
        self.gemini_client = GeminiClient()
        try:
            import pymupdf4llm  # noqa: F401, PLC0415
            self.pymupdf_available = True
        except ImportError:
            self.pymupdf_available = False

    def parse_pdf_to_markdown(self, pdf_path: str) -> str:
        """
        Convierte PDF a Markdown estructurado combinando pymupdf4llm o LLM Vision fallback.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"El archivo PDF no existe en la ruta: {pdf_path}")

        if self.pymupdf_available:
            try:
                import pymupdf4llm  # noqa: PLC0415
                logger.info("Parseando PDF con PyMuPDF4LLM: %s", pdf_path)
                return pymupdf4llm.to_markdown(pdf_path)
            except Exception as exc:
                logger.warning("PyMuPDF4LLM falló (%s). Cambiando a Gemini LLM Parser.", exc)

        return self.parse_pdf_with_llm(pdf_path)["markdown_text"]

    def parse_pdf_with_llm(self, pdf_path: str) -> Dict[str, Any]:
        """
        Utiliza Gemini LLM Multimodal para extraer y reconstruir la estructura pedagógica
        del PDF (Markdown, listas, tablas, fórmulas y conceptos clave).
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"El archivo PDF no existe en la ruta: {pdf_path}")

        logger.info("Parseando PDF con IA LLM Gemini Vision: %s", pdf_path)

        prompt = """
        Analiza el documento técnico adjunto. Realiza un parsing estructurado inteligente:
        1. Extrae todo el contenido conservando la jerarquía de encabezados (#, ##, ###).
        2. Formatea tablas en Markdown estándar.
        3. Identifica bloques de código y organízalos sintácticamente.
        4. Infiere los conceptos clave y un resumen ejecutivo estructurado.
        
        Devuelve el resultado ÚNICAMENTE en formato JSON estricto con esta estructura:
        {
            "markdown_text": "Texto completo traducido/extraído en Markdown estructurado",
            "page_count": 5,
            "detected_tables": 2,
            "key_concepts": ["Concepto 1", "Concepto 2"],
            "summary": "Resumen ejecutivo del documento parseado por la IA"
        }
        """

        system_instruction = (
            "Eres un Parser de Documentos Técnicos asistido por IA de alta precisión. "
            "Reconstruyes manuales en Markdown limpio sin perder datos. Responde solo con JSON válido."
        )

        try:
            raw_response = self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                json_output=True
            )
            raw_response = raw_response.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(raw_response)
            return {
                "markdown_text": parsed.get("markdown_text", ""),
                "page_count": parsed.get("page_count", 1),
                "detected_tables": parsed.get("detected_tables", 0),
                "key_concepts": parsed.get("key_concepts", []),
                "summary": parsed.get("summary", ""),
                "engine": "Gemini 1.5 LLM Vision Parser"
            }
        except Exception as exc:
            logger.error("Fallo en Gemini LLM PDF Parser: %s. Aplicando lectura textual básica.", exc)
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                pages = [p.extract_text() or "" for p in reader.pages]
                text = "\n\n".join(pages)
                return {
                    "markdown_text": f"# {os.path.basename(pdf_path)}\n\n{text}",
                    "page_count": len(pages),
                    "detected_tables": 0,
                    "key_concepts": [],
                    "summary": text[:200] + "...",
                    "engine": "PyPDF Fallback Parser"
                }
            except Exception as err:
                raise RuntimeError(f"Error fatal parseando PDF con IA LLM: {err}") from err
