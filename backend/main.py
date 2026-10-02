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
    if not settings.OCI_ENABLED:
        logger.warning("WARNING: OCI desactivado: almacenamiento local de desarrollo")

# Configurar CORS para permitir peticiones desde el Frontend Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "mensaje": "Bienvenido a NuevaMente API - Sistema Inteligente de Adaptación Educativa",
        "documentacion_swagger": "/docs",
        "version": settings.VERSION
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
