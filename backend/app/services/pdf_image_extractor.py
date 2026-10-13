"""
pdf_image_extractor.py

Purpose:
    Extracts embedded images and diagrams from PDF documents using PyMuPDF (fitz).
    Filters out decorative icons and tiny graphics, saving valid images to disk
    with structured names (e.g. {pdf_name}_p{page}_img{index}.{ext}).

Input:
    - pdf_path (Path or str): Path to the source PDF file.
    - output_dir (Path or str): Destination directory for extracted images.
    - min_width (int): Minimum image width in pixels (defaults to 100).
    - min_height (int): Minimum image height in pixels (defaults to 100).

Output:
    - List of dictionaries containing metadata of extracted images:
      [{"path": str, "page_number": int, "image_index": int, "format": str}]
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def extract_pdf_images(
    pdf_path: str,
    output_dir: str = "./extracted_images",
    min_width: int = 50,
    min_height: int = 50,
) -> List[Dict[str, Any]]:
    """
    Extracts embedded images from a PDF file and writes them to output_dir.
    Skips images below specified dimensions to filter decorative icons.
    """
    try:
        import fitz  # PyMuPDF # noqa: PLC0415
    except ImportError as exc:
        logger.warning("PyMuPDF (fitz) is not installed. Image extraction skipped: %s", exc)
        return []

    source_path = Path(pdf_path)
    if not source_path.exists():
        logger.warning("PDF file not found for image extraction: %s", pdf_path)
        return []

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    extracted_records: List[Dict[str, Any]] = []
    stem = source_path.stem
    total_embedded_found = 0

    try:
        doc = fitz.open(str(source_path))
    except Exception as exc:
        logger.warning("Failed to open PDF %s for image extraction: %s", pdf_path, exc)
        return []

    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_number = page_index + 1
            image_list = page.get_images(full=True)
            total_embedded_found += len(image_list)

            for img_idx, img_info in enumerate(image_list, start=1):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue

                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)

                    # Filter out tiny logos, bullets or 1-pixel rules
                    if width < min_width or height < min_height:
                        logger.debug(
                            "Skipping small image (%dx%d) on page %d of %s",
                            width, height, page_number, pdf_path,
                        )
                        continue

                    image_bytes = base_image.get("image")
                    image_ext = base_image.get("ext", "png")

                    filename = f"{stem}_p{page_number}_img{img_idx}.{image_ext}"
                    image_file_path = target_dir / filename

                    with open(image_file_path, "wb") as img_file:
                        img_file.write(image_bytes)

                    extracted_records.append({
                        "path": str(image_file_path.resolve()),
                        "page_number": page_number,
                        "image_index": img_idx,
                        "format": image_ext,
                        "width": width,
                        "height": height,
                    })
                except Exception as img_err:
                    logger.warning(
                        "Error extracting image xref %s on page %d of %s: %s",
                        xref,
                        page_number,
                        pdf_path,
                        img_err,
                    )
    finally:
        doc.close()

    logger.info(
        "PDF %s: Found %d embedded images total, extracted %d meeting dimension threshold (>=%dx%d). Output: %s",
        source_path.name,
        total_embedded_found,
        len(extracted_records),
        min_width,
        min_height,
        target_dir.resolve(),
    )
    return extracted_records

