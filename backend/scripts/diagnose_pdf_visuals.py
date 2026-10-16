"""
diagnose_pdf_visuals.py

Purpose:
    Diagnoses what visual content a PDF contains and what pymupdf4llm extracts.
    Distinguishes between raster images, vector drawings, and text-based formulas.

Input:
    sys.argv[1]: path to the PDF to diagnose.

Output:
    Console report with image/drawing counts and Markdown content preview.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

PDF_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not PDF_PATH or not PDF_PATH.exists():
    print("Usage: uv run python scripts/diagnose_pdf_visuals.py <path_to_pdf>")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"PDF: {PDF_PATH.name}")
print(f"{'='*60}\n")

# ── 1. PyMuPDF raw analysis ───────────────────────────────────────
try:
    import fitz

    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    total_raster = 0
    total_vector_drawings = 0
    pages_with_raster = []
    pages_with_drawings = []

    print(f"[fitz] Total pages: {total_pages}")

    for page_index in range(total_pages):
        page = doc[page_index]
        page_num = page_index + 1

        images = page.get_images(full=True)
        drawings = page.get_drawings()

        if images:
            total_raster += len(images)
            pages_with_raster.append((page_num, len(images)))
        if drawings:
            total_vector_drawings += len(drawings)
            pages_with_drawings.append((page_num, len(drawings)))

    doc.close()

    print(f"\n RASTER images (PNG/JPEG embedded): {total_raster}")
    if pages_with_raster:
        for pg, count in pages_with_raster[:10]:
            print(f"    Page {pg}: {count} image(s)")
    else:
        print("    None found. Diagrams are likely vector drawings, not bitmaps.")

    print(f"\n VECTOR drawings (lines, shapes, paths): {total_vector_drawings}")
    if pages_with_drawings:
        for pg, count in list(pages_with_drawings)[:10]:
            print(f"    Page {pg}: {count} drawing path(s)")
    else:
        print("    No vector paths found.")

except ImportError:
    print("PyMuPDF (fitz) not installed.")

# ── 2. pymupdf4llm Markdown output ───────────────────────────────
print(f"\n{'='*60}")
print("pymupdf4llm Markdown output (preview first 5 pages)")
print(f"{'='*60}\n")

try:
    import pymupdf4llm

    page_chunks = pymupdf4llm.to_markdown(str(PDF_PATH), page_chunks=True)

    for i, chunk in enumerate(page_chunks[:5]):
        text = chunk.get("text", "").strip()
        if text:
            preview = text[:600].replace("\n", " | ")
            print(f"[Page {i+1}] ({len(text)} chars)\n{preview}\n")

    full_text = "\n".join(c.get("text", "") for c in page_chunks)

    formula_hints = [
        ("LaTeX-style symbols (\\frac, \\int...)", any(s in full_text for s in [r"\frac", r"\int", r"\sum", r"\alpha", r"\beta"])),
        ("Unicode math symbols (U+2200-22FF)", any(0x2200 < ord(c) < 0x22FF for c in full_text)),
        ("Dollar sign equations ($...$ or $$)", "$$" in full_text or "$" in full_text),
        ("Superscript/subscript ASCII", any(s in full_text for s in ["^{", "_{", "^2", "^3"])),
        ("Greek letters (alpha, beta, etc.)", any(s in full_text for s in ["\u03b1", "\u03b2", "\u03b3", "\u03bc", "\u03c3"])),
        ("Mathematical operators", any(s in full_text for s in ["\u2248", "\u2264", "\u2265", "\u221e", "\u2211", "\u222b"])),
    ]

    print(f"\n{'='*60}")
    print("Math / Formula content in Markdown:")
    print(f"{'='*60}")
    for label, found in formula_hints:
        status = "YES" if found else "No "
        print(f"  [{status}]  {label}")

    print(f"\nTotal Markdown: {len(full_text):,} chars across {len(page_chunks)} pages")

except ImportError:
    print("pymupdf4llm not installed.")
except Exception as exc:
    print(f"Error running pymupdf4llm: {exc}")
