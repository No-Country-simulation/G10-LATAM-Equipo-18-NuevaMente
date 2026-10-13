import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

import logging

logger = logging.getLogger("uvicorn")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="API REST del proyecto NuevaMente para el Hackathon ONE G10 (Oracle Next Education & Alura). Módulo de Adaptación de Contenido Técnico con Graph RAG, RAG Híbrido, Gemini y OCI Object Storage Always Free."
)

@app.on_event("startup")
async def startup_event():
    try:
        from app.core.security import init_auth_tables
        init_auth_tables()
        logger.info("Base de datos SQLite y tablas de autenticación/jobs inicializadas.")
    except Exception as exc:
        logger.error("Error inicializando tablas en startup: %s", exc)

    try:
        from app.services.storage import get_storage_backend
        from app.services.storage.oci_backend import OciStorageBackend
        backend = get_storage_backend()
        if isinstance(backend, OciStorageBackend):
            check_rep = backend.self_check()
            logger.info("OCI Object Storage autochequeo al arrancar: %s", check_rep)
        elif not settings.OCI_ENABLED:
            logger.warning("WARNING: OCI desactivado: operando con almacenamiento local de desarrollo")
    except Exception as exc:
        logger.warning("Aviso en chequeo inicial de OCI: %s", exc)

    try:
        from app.services.storage_queue_service import StorageQueueService
        processed = StorageQueueService.get_instance().process_pending_jobs(limit=20)
        if processed > 0:
            logger.info("Trabajos pendientes de OCI procesados al arrancar: %d", processed)
    except Exception as exc:
        logger.warning("Aviso procesando trabajos pendientes: %s", exc)

# Configurar CORS para permitir peticiones desde el Frontend Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/api/v1")
app.include_router(api_router, prefix="/api/api")


@app.get("/")
async def root():
    return {
        "mensaje": "Bienvenido a NuevaMente API - Sistema Inteligente de Adaptación Educativa",
        "documentacion_swagger": "/docs",
        "version": settings.VERSION
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
