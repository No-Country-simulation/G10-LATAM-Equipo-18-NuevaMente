"""
trash.py

Purpose:
    FastAPI router endpoints for trash management, soft deletion,
    restoration, permanent deletion, empty trash, and listing trashed packages.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.api.v1.dependencies import get_current_user
from app.services.trash_service import TrashService

router = APIRouter()
trash_service = TrashService()

# Simple rate limiter dictionary for empty_trash endpoint (max 5 requests per 60s per user)
_EMPTY_TRASH_LIMITS: Dict[str, List[float]] = {}


def check_empty_trash_rate_limit(user_id: str) -> None:
    import time
    now = time.time()
    history = _EMPTY_TRASH_LIMITS.get(user_id, [])
    history = [t for t in history if now - t < 60]

    if len(history) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "status": "error",
                "codigo": "RATE_LIMIT_EXCEEDED",
                "mensaje": "Demasiadas solicitudes de vaciado de papelera. Intente nuevamente en un minuto."
            }
        )
    history.append(now)
    _EMPTY_TRASH_LIMITS[user_id] = history


@router.delete("/contenidos/{content_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
@router.delete("/api/contenidos/{content_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK, include_in_schema=False)
async def move_to_trash(
    content_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Moves an educational content package to trash (soft delete).
    Idempotent.
    """
    return trash_service.move_to_trash(user_id=current_user["id"], content_id=content_id)


@router.get("/papelera", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
@router.get("/api/papelera", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK, include_in_schema=False)
async def list_trash(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lists all non-expired trashed packages belonging to the current user.
    Applies lazy backup purge for expired items.
    """
    return trash_service.list_trash(user_id=current_user["id"])


@router.post("/papelera/{content_id}/restore", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
@router.post("/api/papelera/{content_id}/restore", response_model=Dict[str, Any], status_code=status.HTTP_200_OK, include_in_schema=False)
async def restore_content(
    content_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Restores a content package from trash back to the active library.
    """
    return trash_service.restore_content(user_id=current_user["id"], content_id=content_id)


@router.delete("/papelera/{content_id}", status_code=status.HTTP_200_OK)
@router.delete("/api/papelera/{content_id}", status_code=status.HTTP_200_OK, include_in_schema=False)
async def delete_permanently(
    content_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Permanently deletes a single item from trash and OCI Object Storage.
    """
    success = trash_service.delete_permanently(user_id=current_user["id"], content_id=content_id)
    return {
        "status": "exito",
        "mensaje": f"Contenido '{content_id}' eliminado definitivamente.",
        "id": content_id
    }


@router.delete("/papelera", status_code=status.HTTP_200_OK)
@router.delete("/api/papelera", status_code=status.HTTP_200_OK, include_in_schema=False)
async def empty_trash(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Empties all items in the user's trash permanently.
    Rate limited.
    """
    check_empty_trash_rate_limit(current_user["id"])
    count = trash_service.empty_trash(user_id=current_user["id"])
    return {
        "status": "exito",
        "mensaje": f"Se eliminaron definitivamente {count} elementos de la papelera.",
        "elementos_eliminados": count
    }
