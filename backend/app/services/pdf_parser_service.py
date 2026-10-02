"""
pdf_parser_service.py

Purpose:
    Converts a PDF into structured Markdown (headings, lists, tables) with
    pymupdf4llm, so IngesterService can split it by section headings into
    parent and child chunks. Running headers and footers that repeat across
    pages are removed before returning, using the same remove_repeated_lines()
    from text_cleaner that the ingester applies to its plain-text extraction.

    This service is an optional first choice, not the only path: when
    pymupdf4llm is not installed (is_available is False), or a specific file
    cannot be converted (an exception is raised), IngesterService falls back
    to its own pypdf plain-text extraction, which adds page markers. No LLM
    is involved.

Input:
    - pdf_path (str): path to a PDF already validated by IngesterService
      (supported extension and maximum size).

Output:
    - is_available (bool): whether pymupdf4llm could be imported.
    - parse_pdf_to_markdown(): the whole document as one Markdown string.
      Raises FileNotFoundError if the path does not exist, RuntimeError if
      pymupdf4llm is not installed, and ValueError if the PDF has no
      extractable text (for example, a scanned or image-only PDF).
"""

import logging
from pathlib import Path

from app.services.text_cleaner import remove_repeated_lines

logger = logging.getLogger(__name__)


class PdfParserService:
    """Markdown extraction from PDFs using pymupdf4llm."""

    def __init__(self):
        self._pymupdf4llm = self._import_pymupdf4llm()

    @staticmethod
    def _import_pymupdf4llm():
        """Returns the pymupdf4llm module, or None (with the reason logged) if it cannot be imported."""
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

    def parse_pdf_to_markdown(self, pdf_path: str) -> str:
        """
        Converts the PDF to Markdown and removes repeated page headers/footers.
        Any conversion error is raised, not swallowed, so the caller can fall back.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if not self.is_available:
            raise RuntimeError("pymupdf4llm is not installed.")

        logger.info("Parsing PDF with pymupdf4llm: %s", path.name)

        # One Markdown string per page, which repeated header/footer detection needs.
        page_chunks = self._pymupdf4llm.to_markdown(str(path), page_chunks=True)
        pages = [chunk.get("text", "") for chunk in page_chunks]
        # Markdown structure (headings, tables, lists) is kept even when it repeats.
        pages = remove_repeated_lines(pages, protect_markdown_structure=True)

        markdown = "\n\n".join(page.strip() for page in pages if page.strip())
        if not markdown:
            raise ValueError(
                f"No extractable text found in {path.name} (it may be a scanned or image-only PDF)."
            )

        return markdown