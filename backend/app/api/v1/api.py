from fastapi import APIRouter
from app.api.v1.endpoints import adaptation, ingestion, health, multimodal, auth, anki, trash

api_router = APIRouter()
api_router.include_router(adaptation.router, tags=["Adaptación Educativa"])
api_router.include_router(ingestion.router, tags=["Ingestión de Documentos"])
api_router.include_router(multimodal.router, tags=["Multimodal & Visión"])
api_router.include_router(health.router, tags=["Estado del Sistema"])
api_router.include_router(auth.router, tags=["Autenticación de Usuarios"])
api_router.include_router(anki.router, tags=["Integración Anki Flashcards"])
api_router.include_router(trash.router, tags=["Papelera y Borrado Lógico"])

