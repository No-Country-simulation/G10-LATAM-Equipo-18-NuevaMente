"""
api.py

Purpose:
    Composes the v1 API router from the active endpoint modules.

Input:
    None (router registration).

Output:
    api_router: the APIRouter that main.py mounts under the API prefixes.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    documents,
    contents,
    adaptation,
    ingestion,
    multimodal,
    health,
    auth,
    anki,
    trash,
    storage,
)

api_router = APIRouter()
api_router.include_router(documents.router, tags=["Documentos y Generación RAG"])
api_router.include_router(contents.router, tags=["Biblioteca de Contenidos"])
api_router.include_router(adaptation.router, tags=["Adaptación Educativa"])
api_router.include_router(ingestion.router, tags=["Ingestión de Documentos"])
api_router.include_router(multimodal.router, tags=["Multimodal & Visión"])
api_router.include_router(health.router, tags=["Estado del Sistema"])
api_router.include_router(auth.router, tags=["Autenticación de Usuarios"])
api_router.include_router(anki.router, tags=["Integración Anki Flashcards"])
api_router.include_router(trash.router, tags=["Papelera y Borrado Lógico"])
api_router.include_router(storage.router, tags=["Almacenamiento OCI Object Storage"])
