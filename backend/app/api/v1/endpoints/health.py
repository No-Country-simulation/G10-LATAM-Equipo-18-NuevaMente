from fastapi import APIRouter
from scripts.check_services import check_all_services

router = APIRouter()

@router.get("/health")
async def health_check():
    from app.core.config import settings
    return {
        "status": "healthy",
        "service": "NuevaMente API Engine",
        "version": settings.VERSION,
        "oci_always_free": "activo" if settings.OCI_ENABLED else "desactivado (local)",
        "gemini_pipeline": "listo"
    }

@router.get("/salud/servicios")
async def salud_servicios():
    """Retorna el diagnóstico completo de salud de servicios sin exponer secretos."""
    return check_all_services()
