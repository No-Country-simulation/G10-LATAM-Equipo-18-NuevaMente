"""
contents.py

Purpose:
    HTTP surface for the authenticated user's active content library. The
    generation pipeline records every adapted package in the `contenidos`
    table, so the Library view reads that table instead of trusting client
    state; the Trash view reads the same table through trash.py.

Input:
    - GET /contenidos: requires an authenticated user; lists the caller's
      active (non-trashed) packages.
    - GET /contenidos/{content_id}: requires an authenticated user; returns a
      single owned package.

Output:
    JSON packages with their metadata plus `contenido_adaptado`, the adapted
    content parsed from the stored payload, matching what the frontend renders,
    and `evaluacion_calidad`/`metadatos` (real RAG anchoring score, models used)
    taken from the full response persisted at generation time.
"""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_current_user
from app.services.trash_service import TrashService

router = APIRouter()
trash_service = TrashService()


def _serialize_content(row: Dict[str, Any]) -> Dict[str, Any]:
    """Maps a `contenidos` row to the HTTP shape the frontend consumes."""
    contenido_adaptado: Any = None
    raw_content = row.get("content")
    if raw_content:
        try:
            contenido_adaptado = json.loads(raw_content)
        except (TypeError, ValueError):
            # Invalid/legacy payloads must not break the whole library list.
            contenido_adaptado = None

    # `response_json` holds the full AdaptationResponse payload written at
    # generation time. Rows created before it existed simply return null here.
    evaluacion_calidad: Any = None
    metadatos: Any = None
    raw_response = row.get("response_json")
    if raw_response:
        try:
            full_response = json.loads(raw_response)
        except (TypeError, ValueError):
            full_response = None
        if isinstance(full_response, dict):
            evaluacion_calidad = full_response.get("evaluacion_calidad")
            metadatos = full_response.get("metadatos")

    return {
        "content_id": row.get("id"),
        "user_id": row.get("user_id"),
        "title": row.get("title"),
        "recipient_profile": row.get("recipient_profile"),
        "output_format": row.get("output_format"),
        "niche": row.get("niche"),
        "detail_level": row.get("detail_level"),
        "status": row.get("status"),
        "object_key_json": row.get("object_key_json"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "deleted_at": row.get("deleted_at"),
        "purge_at": row.get("purge_at"),
        "contenido_adaptado": contenido_adaptado,
        "evaluacion_calidad": evaluacion_calidad,
        "metadatos": metadatos,
    }


@router.get("/contenidos", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def list_contents(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Lists the caller's active (non-trashed) educational packages."""
    rows = trash_service.list_active(user_id=current_user["id"])
    return [_serialize_content(row) for row in rows]


@router.get("/contenidos/{content_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_content(content_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns one educational package owned by the caller."""
    row = trash_service.get_content(user_id=current_user["id"], content_id=content_id)
    return _serialize_content(row)
