"""
pdf_parser_service.py

Purpose:
    Converts a PDF into structured Markdown (headings, lists, tables) with
    pymupdf4llm, so IngesterService can split it by section headings into
    parent and child chunks. Running headers and footers that repeat across
    pages are removed before returning, matching the cleanup the ingester
    applies to its plain-text extraction.

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
import re
from collections import Counter
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# A page line is treated as a running header/footer when it repeats on at
# least this share of the pages (same rule as IngesterService.remove_repeated_lines).
_MIN_REPETITION_RATIO = 0.4
_MIN_PAGES_FOR_NOISE_REMOVAL = 3

# Markdown structure that is never removed even when it repeats across pages:
# headings, table rows, list items, block quotes, code fences and numbered items.
_MARKDOWN_STRUCTURE = re.compile(r"^(#{1,6}\s|\||[-*+]\s|>|```|\d+[.)]\s)")


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
        pages = self._remove_repeated_page_lines(pages)

        markdown = "\n\n".join(page.strip() for page in pages if page.strip())
        if not markdown:
            raise ValueError(
                f"No extractable text found in {path.name} (it may be a scanned or image-only PDF)."
            )

        return markdown

    @staticmethod
    def _remove_repeated_page_lines(pages: List[str]) -> List[str]:
        """
        Strips plain-text lines that repeat across pages (running headers and
        footers). Markdown structure lines are kept even when they repeat, so
        recurring headings and table separators are not damaged.
        """
        if len(pages) < _MIN_PAGES_FOR_NOISE_REMOVAL:
            return pages

        line_counts: Counter = Counter()
        for page in pages:
            line_counts.update({line.strip() for line in page.split("\n") if line.strip()})

        threshold = max(2, int(len(pages) * _MIN_REPETITION_RATIO))
        noisy_lines = {
            line for line, count in line_counts.items()
            if count >= threshold and not _MARKDOWN_STRUCTURE.match(line)
        }

        return [
            "\n".join(line for line in page.split("\n") if line.strip() not in noisy_lines)
            for page in pages
        ]