"""
storage.py

Endpoints para gestión y consulta del almacenamiento en OCI Object Storage Always Free.
Provee:
  - GET /api/almacenamiento/estado/{content_id}: consulta el estado de guardado (pendiente, completado, error).
  - POST /api/almacenamiento/reintentar/{content_id}: reintenta trabajos fallidos.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any

from app.services.storage_queue_service import StorageQueueService
from app.core.security import get_current_user_optional

router = APIRouter()


@router.get("/almacenamiento/estado/{content_id}", status_code=status.HTTP_200_OK)
async def get_storage_status(content_id: str):
    """
    Retorna el estado de persistencia real en OCI Object Storage Always Free
    para un artefacto educativo y sus documentos asociados.
    """
    queue_service = StorageQueueService.get_instance()
    info = queue_service.get_content_status(content_id)
    if info.get("status_upload") == "no_encontrado":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró registro de persistencia para el contenido '{content_id}'.",
        )
    return info


@router.post("/almacenamiento/reintentar/{content_id}", status_code=status.HTTP_200_OK)
async def retry_storage_job(
    content_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    Reencola y reintenta de inmediato los trabajos de persistencia que hayan fallado
    para un contenido específico.
    """
    user_id = current_user.get("id") if current_user else None
    queue_service = StorageQueueService.get_instance()
    ok = queue_service.retry_content(content_id=content_id, user_id=user_id)

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay trabajos fallidos pendientes para reintentar o no eres el propietario.",
        )

    return {
        "status": "exito",
        "mensaje": f"Reintento de persistencia disparado para el contenido '{content_id}'.",
        "estado_actual": queue_service.get_content_status(content_id),
    }
