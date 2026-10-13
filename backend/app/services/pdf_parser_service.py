"""
pdf_parser_service.py

Purpose:
    Converts a PDF into structured Markdown (headings, lists, tables) with
    pymupdf4llm, so IngesterService can split it by section headings into
    parent and child chunks. Running headers and footers that repeat across
    pages are removed before returning, using the same remove_repeated_lines()
    from text_cleaner that the ingester applies to its plain-text extraction.

    Additionally extracts embedded diagrams/images to a destination folder
    and optionally executes multimodal vision inspection to append diagram
    descriptions to the returned Markdown.

Input:
    - pdf_path (str): path to a PDF already validated by IngesterService.
    - use_ai_vision (bool): whether to describe extracted images with multimodal AI.
    - image_output_dir (str): destination directory for extracted images.

Output:
    - is_available (bool): whether pymupdf4llm could be imported.
    - parse_pdf_to_markdown(): the whole document as one Markdown string.
"""

import logging
from pathlib import Path

from app.services.pdf_image_extractor import extract_pdf_images
from app.services.pdf_vision_service import PdfVisionService
from app.services.text_cleaner import remove_repeated_lines

logger = logging.getLogger(__name__)


class PdfParserService:
    """Markdown extraction from PDFs using pymupdf4llm, with optional image extraction and vision analysis."""

    def __init__(self):
        self._pymupdf4llm = self._import_pymupdf4llm()
        self._vision_service = PdfVisionService()
        self.last_extracted_images = []

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

    def extract_images(self, pdf_path: str, output_dir: str = "./extracted_images"):
        """Extracts embedded images from the PDF to the designated output folder."""
        return extract_pdf_images(pdf_path=pdf_path, output_dir=output_dir)

    def parse_pdf_to_markdown(
        self,
        pdf_path: str,
        use_ai_vision: bool = False,
        image_output_dir: str = "./extracted_images",
    ) -> str:
        """
        Converts the PDF to Markdown and removes repeated page headers/footers.
        Optionally extracts embedded images and enriches the Markdown with diagram descriptions.
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

        # Image extraction and optional visual multimodal processing
        self.last_extracted_images = []
        try:
            images = self.extract_images(str(path), output_dir=image_output_dir)
            self.last_extracted_images = images
            if use_ai_vision and images:
                appendix = self._vision_service.build_visual_appendix(images)
                if appendix:
                    markdown += appendix
        except Exception as exc:
            logger.warning("Image extraction or vision analysis failed for %s: %s", path.name, exc)

        return markdown