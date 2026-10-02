"""
pdf_parser_service.py

Converts a PDF into structured Markdown (headings, lists, tables) with
pymupdf4llm, applying Unicode NFKC normalization, ligature restitution,
running header/footer removal (>50% pages), presentation slide grouping,
and scanned PDF detection (<50 chars total).
"""

import logging
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Running header/footer threshold: lines repeating across at least 50% of pages
_MIN_REPETITION_RATIO = 0.5
_MIN_PAGES_FOR_NOISE_REMOVAL = 3

# Markdown structure that is kept even when repeated:
# headings, table rows, list items, block quotes, code fences, numbered items.
_MARKDOWN_STRUCTURE = re.compile(r"^(#{1,6}\s|\||[-*+]\s|>|```|\d+[.)]\s)")


def normalize_extracted_text(text: str) -> str:
    """
    Restituye ligaduras tipográficas (ﬁ ﬂ ﬀ ﬃ ﬄ), aplica normalización NFKC,
    y une palabras cortadas por guion al final de línea.
    """
    if not text:
        return ""
        
    # 1. Restitución explícita de ligaduras
    text = (
        text.replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
        .replace("ﬀ", "ff")
        .replace("ﬃ", "ffi")
        .replace("ﬄ", "ffl")
    )
    
    # 2. Corrección de desarticulaciones comunes de ligaduras (ej. con guración -> configuración)
    text = re.sub(r'\bcon\s+guraci([oó]n)\b', r'configuraci\1', text, flags=re.IGNORECASE)
    
    # 3. Normalización Unicode NFKC
    text = unicodedata.normalize("NFKC", text)
    
    # 4. Unión de palabras cortadas por guion al final de línea (palabra-\nlinea -> palabralinea)
    text = re.sub(r'(\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]+)-\n([a-zA-ZáéíóúÁÉÍÓÚñÑ]+\b)', r'\1\2', text)
    
    return text


class PdfParserService:
    """Markdown extraction from PDFs using pymupdf4llm."""

    def __init__(self):
        self._pymupdf4llm = self._import_pymupdf4llm()

    @staticmethod
    def _import_pymupdf4llm():
        """Returns the pymupdf4llm module, or None if it cannot be imported."""
        try:
            import pymupdf4llm  # noqa: PLC0415
            return pymupdf4llm
        except ImportError as exc:
            logger.warning("pymupdf4llm is unavailable (%s). PDFs will use plain-text extraction.", exc)
            return None

    @property
    def is_available(self) -> bool:
        """True when pymupdf4llm was imported successfully."""
        return self._pymupdf4llm is not None

    def parse_pdf_to_markdown(self, pdf_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Convierte el PDF a Markdown estructurado y retorna (markdown_text, resumen_ingesta).
        Aplica limpieza de encabezados/pies repetidos (>50%), normalización NFKC,
        agrupamiento de diapositivas si es tipo presentación, y detección de PDFs escaneados.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if not self.is_available:
            raise RuntimeError("pymupdf4llm is not installed.")

        logger.info("Parsing PDF with pymupdf4llm: %s", path.name)

        page_chunks = self._pymupdf4llm.to_markdown(str(path), page_chunks=True)
        raw_pages = [chunk.get("text", "") for chunk in page_chunks]
        
        # 1. Normalización por página
        norm_pages = [normalize_extracted_text(p) for p in raw_pages]
        
        # 2. Eliminación de encabezados y pies repetidos en >50% de páginas
        clean_pages = self._remove_repeated_page_lines(norm_pages)

        # 3. Detección de PDF escaneado (< 50 caracteres en total)
        total_chars = sum(len(p.strip()) for p in clean_pages)
        num_pages = len(clean_pages)
        avg_chars_per_page = round(total_chars / max(1, num_pages))

        if total_chars < 50:
            raise ValueError("No pudimos leer texto de este PDF (puede ser un documento escaneado o solo imágenes).")

        # 4. Manejo de PDF tipo presentación (< 600 caracteres de media por página)
        is_presentation = avg_chars_per_page < 600
        if is_presentation:
            markdown = self._group_presentation_slides(clean_pages)
        else:
            markdown = "\n\n".join(page.strip() for page in clean_pages if page.strip())

        # Calidad de texto
        if avg_chars_per_page >= 300:
            calidad_texto = "buena"
        elif avg_chars_per_page >= 100:
            calidad_texto = "limitada"
        else:
            calidad_texto = "insuficiente"

        warnings: List[str] = []
        if is_presentation:
            warnings.append("Formato presentación detectado: agrupando diapositivas por secciones.")

        resumen_ingesta = {
            "paginas": num_pages,
            "caracteres": total_chars,
            "caracteres_por_pagina": avg_chars_per_page,
            "secciones": len(re.findall(r'^(#{1,6}\s|\*\* Diapositiva)', markdown, re.MULTILINE)) or 1,
            "calidad_texto": calidad_texto,
            "es_presentacion": is_presentation,
            "advertencias": warnings,
        }

        return markdown, resumen_ingesta

    @staticmethod
    def _remove_repeated_page_lines(pages: List[str]) -> List[str]:
        """Elimina líneas repetidas en el >=50% de las páginas (encabezados/pies)."""
        if len(pages) < _MIN_PAGES_FOR_NOISE_REMOVAL:
            return pages

        line_counts: Counter = Counter()
        for page in pages:
            unique_lines = {line.strip() for line in page.split("\n") if line.strip()}
            line_counts.update(unique_lines)

        threshold = max(2, int(len(pages) * _MIN_REPETITION_RATIO))
        noisy_lines = {
            line for line, count in line_counts.items()
            if count >= threshold and not _MARKDOWN_STRUCTURE.match(line)
        }

        return [
            "\n".join(line for line in page.split("\n") if line.strip() not in noisy_lines)
            for page in pages
        ]

    @staticmethod
    def _group_presentation_slides(pages: List[str]) -> str:
        """Agrupa diapositivas consecutivas de presentación en bloques estructurados por título."""
        structured_sections = []
        for i, page in enumerate(pages, 1):
            lines = [l.strip() for l in page.split("\n") if l.strip()]
            if not lines:
                continue
            
            # Buscar posible título en las primeras dos líneas
            first_line = lines[0]
            if first_line.startswith("#"):
                header = first_line
                body = "\n".join(lines[1:])
            else:
                header = f"## Diapositiva {i}: {first_line[:60]}"
                body = "\n".join(lines[1:])
                
            structured_sections.append(f"{header}\n{body}")

        return "\n\n".join(structured_sections)
