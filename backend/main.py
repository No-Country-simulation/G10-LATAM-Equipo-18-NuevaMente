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
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
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

# Configurar CORS permisivo para desarrollo y produccion en Oracle Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://127.0.0.1",
        "http://40.233.19.229",
        "http://40.233.19.229:80",
        "http://40.233.19.229:8000",
        "https://40.233.19.229",
    ],
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas API: Registrar de manera canonica en el esquema OpenAPI bajo /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Alias de compatibilidad (ocultos del schema OpenAPI para no duplicar ni saturar Swagger UI)
app.include_router(api_router, prefix="/api", include_in_schema=False)
app.include_router(api_router, prefix="/api/api/v1", include_in_schema=False)
app.include_router(api_router, prefix="/api/api", include_in_schema=False)

# Alias de documentacion y OpenAPI JSON para compatibilidad con proxies y clientes
@app.get("/api/v1/openapi.json", include_in_schema=False)
@app.get("/api/openapi.json", include_in_schema=False)
async def openapi_alias():
    from fastapi.responses import JSONResponse
    return JSONResponse(app.openapi())

@app.get("/api/docs", include_in_schema=False)
@app.get("/api/v1/docs", include_in_schema=False)
async def docs_alias():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/")
async def root():
    return {
        "mensaje": "Bienvenido a NuevaMente API - Sistema Inteligente de Adaptación Educativa",
        "documentacion_swagger": "/docs",
        "version": settings.VERSION
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
