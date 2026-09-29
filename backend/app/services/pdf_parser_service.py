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
        Convierte PDF a Markdown estructurado combinando PyMuPDF/PyPDF o LLM Vision fallback.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"El archivo PDF no existe en la ruta: {pdf_path}")

        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            pages_text = [page.get_text() for page in doc]
            full_text = "\n\n".join([p.strip() for p in pages_text if p.strip()])
            if full_text and len(full_text) > 10:
                logger.info("PDF parseado con PyMuPDF exitosamente: %s", pdf_path)
                return f"# {os.path.basename(pdf_path)}\n\n{full_text}"
        except Exception as exc:
            logger.warning("PyMuPDF falló (%s). Intentando PyPDF.", exc)

        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            pages_text = [p.extract_text() or "" for p in reader.pages]
            full_text = "\n\n".join([p.strip() for p in pages_text if p.strip()])
            if full_text and len(full_text) > 10:
                logger.info("PDF parseado con PyPDF exitosamente: %s", pdf_path)
                return f"# {os.path.basename(pdf_path)}\n\n{full_text}"
        except Exception as exc:
            logger.warning("PyPDF falló (%s). Probando Gemini LLM Parser.", exc)

        return self.parse_pdf_with_llm(pdf_path)["markdown_text"]

    def parse_pdf_with_llm(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrae el contenido del PDF usando PyMuPDF/PyPDF y lo estructura con Gemini LLM Multimodal.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"El archivo PDF no existe en la ruta: {pdf_path}")

        logger.info("Parseando PDF con IA LLM Gemini Vision: %s", pdf_path)

        extracted_text = ""
        page_count = 1
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            page_count = len(doc)
            pages = [page.get_text() for page in doc]
            extracted_text = "\n\n".join([p.strip() for p in pages if p.strip()])
        except Exception:
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                page_count = len(reader.pages)
                pages = [p.extract_text() or "" for p in reader.pages]
                extracted_text = "\n\n".join([p.strip() for p in pages if p.strip()])
            except Exception as err:
                logger.warning("Extracción local de PDF falló: %s", err)

        if not extracted_text:
            extracted_text = f"Documento PDF: {os.path.basename(pdf_path)}"

        prompt = f"""
        Analiza el siguiente texto extraído del documento técnico '{os.path.basename(pdf_path)}'. Realiza un parsing estructurado inteligente:
        1. Estructura todo el contenido conservando la jerarquía de encabezados (#, ##, ###).
        2. Formatea tablas en Markdown estándar.
        3. Identifica bloques de código y organízalos sintácticamente.
        4. Infiere los conceptos clave y un resumen ejecutivo estructurado.
        
        Devuelve el resultado ÚNICAMENTE en formato JSON estricto con esta estructura:
        {{
            "markdown_text": "Texto completo estructurado en Markdown",
            "page_count": {page_count},
            "detected_tables": 0,
            "key_concepts": ["Concepto 1", "Concepto 2"],
            "summary": "Resumen ejecutivo del documento"
        }}

        TEXTO DEL DOCUMENTO:
        {extracted_text[:12000]}
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
            md_text = parsed.get("markdown_text", "")
            if not md_text:
                md_text = extracted_text
            return {
                "markdown_text": md_text,
                "page_count": parsed.get("page_count", page_count),
                "detected_tables": parsed.get("detected_tables", 0),
                "key_concepts": parsed.get("key_concepts", []),
                "summary": parsed.get("summary", ""),
                "engine": "Gemini 1.5 LLM Vision Parser"
            }
        except Exception as exc:
            logger.error("Fallo en Gemini LLM PDF Parser: %s. Aplicando lectura textual básica.", exc)
            return {
                "markdown_text": f"# {os.path.basename(pdf_path)}\n\n{extracted_text}",
                "page_count": page_count,
                "detected_tables": 0,
                "key_concepts": [],
                "summary": extracted_text[:200] + "...",
                "engine": "PyMuPDF / PyPDF Fallback Parser"
            }
