"""
export.py

Purpose:
    FastAPI endpoints for Multiformat Export in NuevaMente:
    - Direct Markdown download (.md)
    - Direct Anki-compatible CSV deck download (.csv)
    - Direct Formatted Didactic PDF download (.pdf)
"""

import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.v1.dependencies import get_current_user_optional
from app.services.export_service import ExportService, slugify_title
from app.services.trash_service import TrashService

router = APIRouter(prefix="/export", tags=["Exportación Multiformato"])
export_service = ExportService()
trash_service = TrashService()


@router.post("/markdown", summary="Descarga directa en Markdown didáctico")
async def export_markdown_endpoint(payload: Dict[str, Any]):
    """Generates and streams a formatted Markdown (.md) file directly to the browser."""
    try:
        title = (payload.get("contenido_adaptado") or {}).get("titulo") or "contenido"
        slug = slugify_title(title)
        md_content = export_service.export_to_markdown(payload)

        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{slug}.md"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando a Markdown: {exc}",
        )


@router.post("/anki-csv", summary="Descarga directa en CSV compatible con Anki")
async def export_anki_csv_endpoint(payload: Dict[str, Any]):
    """Generates and streams an Anki-compatible CSV deck (.csv) directly to the browser."""
    try:
        title = (payload.get("contenido_adaptado") or {}).get("titulo") or "contenido"
        slug = slugify_title(title)
        csv_content = export_service.export_to_anki_csv(payload)

        # Include UTF-8 BOM so Excel and Anki render Spanish accents perfectly
        bom_csv = "\ufeff" + csv_content

        return Response(
            content=bom_csv.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{slug}-anki.csv"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando a Anki CSV: {exc}",
        )


@router.post("/pdf", summary="Descarga directa en PDF didáctico formateado")
async def export_pdf_endpoint(payload: Dict[str, Any]):
    """Generates and streams a formatted didactic PDF (.pdf) directly to the browser."""
    try:
        title = (payload.get("contenido_adaptado") or {}).get("titulo") or "contenido"
        slug = slugify_title(title)
        pdf_bytes = export_service.export_to_pdf_bytes(payload)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{slug}.pdf"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando a PDF: {exc}",
        )


@router.get("/{export_format}/{content_id}", summary="Descarga directa de contenido guardado por ID")
async def export_by_id_endpoint(
    export_format: str,
    content_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    Downloads a previously saved content package in the requested format (markdown, pdf, anki).
    """
    fmt = export_format.lower().strip()
    if fmt not in {"markdown", "md", "pdf", "anki", "anki-csv", "csv"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de exportación no soportado: '{export_format}'. Use 'markdown', 'pdf' o 'anki'.",
        )

    user_id = current_user.get("id", "usr_anonimo") if current_user else "usr_anonimo"
    row = trash_service.get_content(user_id=user_id, content_id=content_id)
    if not row:
        # Try finding row across users if not in private scope
        with trash_service._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
            found = cursor.fetchone()
            if found:
                row = dict(found)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el contenido '{content_id}'.",
        )

    payload: Dict[str, Any] = {}
    if row.get("response_json"):
        try:
            payload = json.loads(row["response_json"])
        except Exception:
            payload = {}

    if not payload and row.get("content"):
        try:
            adapted = json.loads(row["content"])
            payload = {
                "contenido_adaptado": adapted,
                "metadatos": {
                    "perfil_aplicado": row.get("recipient_profile", "General"),
                    "formato_generado": row.get("output_format", "Educativo"),
                },
                "evaluacion_calidad": {},
            }
        except Exception:
            payload = {}

    if fmt in {"markdown", "md"}:
        return await export_markdown_endpoint(payload)
    elif fmt == "pdf":
        return await export_pdf_endpoint(payload)
    else:
        return await export_anki_csv_endpoint(payload)
