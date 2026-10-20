"""
export.py

Purpose:
    Provides HTTP endpoints for generating and downloading educational documents in binary formats (PDF).

Input:
    Adapted content or full adaptation response payload.

Output:
    Downloadable binary stream (application/pdf).
"""

import re
import unicodedata
from typing import Union
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.schemas.adaptation import AdaptedContent, AdaptationResponse
from app.services.pdf_export_service import PDFExportService

router = APIRouter()


def _sanitize_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    cleaned = re.sub(r"[^\w\s-]", "", normalized).strip().lower()
    return re.sub(r"[-\s]+", "-", cleaned) or "contenido-educativo"


@router.post("/export/pdf", summary="Generar y descargar documento educativo en formato PDF")
def export_pdf(payload: Union[AdaptationResponse, AdaptedContent]):
    """
    Receives educational content and renders a formatted PDF with cover, table of contents,
    and stylized content items using PDFExportService.
    """
    try:
        content: AdaptedContent = (
            payload.adapted_content
            if isinstance(payload, AdaptationResponse)
            else payload
        )

        pdf_service = PDFExportService()
        pdf_bytes = pdf_service.generate_pdf_bytes(content)

        file_title = _sanitize_filename(content.title or "material-educativo")
        filename = f"{file_title}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el documento PDF: {str(exc)}"
        )
