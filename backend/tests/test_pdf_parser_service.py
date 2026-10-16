"""
test_pdf_parser_service.py

Purpose:
    Unit tests for PdfParserService verifying default Markdown output,
    robust image extraction, fallback behavior, and multimodal vision appendix.

Input:
    - Mocked pymupdf4llm, fitz, and GeminiClient responses.

Output:
    - Pytest assertion results validating PdfParserService contracts.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.services.pdf_parser_service import PdfParserService


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Creates a dummy PDF file for path existence validation."""
    pdf_file = tmp_path / "sample_doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy content")
    return pdf_file


def test_parse_pdf_to_markdown_default_behavior(sample_pdf: Path):
    """Verifies that parse_pdf_to_markdown returns clean Markdown by default without vision appendix."""
    service = PdfParserService()
    service._pymupdf4llm = MagicMock()
    service._pymupdf4llm.to_markdown.return_value = [
        {"text": "# Section 1\nContent of page 1"},
        {"text": "## Section 2\nContent of page 2"},
    ]

    result = service.parse_pdf_to_markdown(str(sample_pdf))

    assert isinstance(result, str)
    assert "# Section 1" in result
    assert "## Section 2" in result
    assert "Extracted Visual Context and Diagrams" not in result


def test_parse_pdf_to_markdown_with_vision(sample_pdf: Path, tmp_path: Path):
    """Verifies that setting use_ai_vision=True appends the structured visual descriptions."""
    service = PdfParserService()
    service._pymupdf4llm = MagicMock()
    service._pymupdf4llm.to_markdown.return_value = [{"text": "# Architecture\nDocument text"}]

    mock_images = [
        {"path": str(tmp_path / "img1.png"), "page_number": 1, "image_index": 1}
    ]

    with patch.object(service, "extract_images", return_value=mock_images):
        with patch.object(
            service._vision_service,
            "describe_image",
            return_value="Flowchart showing client-server interaction.",
        ):
            output = service.parse_pdf_to_markdown(
                str(sample_pdf),
                use_ai_vision=True,
                image_output_dir=str(tmp_path / "images"),
            )

    assert "# Architecture" in output
    assert "## Extracted Visual Context and Diagrams" in output
    assert "Figure (Page 1, Image 1)" in output
    assert "Flowchart showing client-server interaction." in output


def test_parse_pdf_to_markdown_resilience_on_vision_failure(sample_pdf: Path):
    """Verifies that an error during image extraction does not disrupt the text Markdown parsing."""
    service = PdfParserService()
    service._pymupdf4llm = MagicMock()
    service._pymupdf4llm.to_markdown.return_value = [{"text": "# Resilient Title\nBody text"}]

    with patch.object(service, "extract_images", side_effect=RuntimeError("Corrupt image data")):
        output = service.parse_pdf_to_markdown(str(sample_pdf), use_ai_vision=True)

    # Markdown is still returned successfully despite image extraction error
    assert "# Resilient Title" in output
    assert "Body text" in output
    assert "Extracted Visual Context and Diagrams" not in output
