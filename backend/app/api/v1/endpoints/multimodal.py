import tempfile
import os
from pathlib import Path
import json
import anyio
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.infrastructure.llm import GeminiClient
from app.core.config import settings

router = APIRouter()
gemini_client = GeminiClient()


def _analyze_diagram_sync(content_bytes: bytes, extension: str, prompt: str, system_instruction: str) -> dict:
    """Writes image to a temp file and invokes Gemini vision synchronously in a worker thread."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_file.write(content_bytes)
        temp_path = temp_file.name

    try:
        raw_response = gemini_client.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            model_name=settings.DEFAULT_GEMINI_MODEL_PRO,
            json_output=True,
            image_path=temp_path,
        )
        cleaned = raw_response.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/extract-diagram", status_code=status.HTTP_200_OK)
async def extract_diagram(file: UploadFile = File(...)):
    """
    Recibe una imagen (ej. Diagrama de AWS/OCI, Arquitectura),
    usa la capacidad multimodal de Gemini 1.5 Flash/Pro para analizarla,
    y devuelve Flashcards de Anki estructuradas en JSON.
    """
    filename = file.filename or "diagrama.jpg"
    extension = Path(filename).suffix.lower()

    if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de imagen no compatible: {extension}. Solo JPG, PNG, WEBP."
        )

    try:
        content_bytes = await file.read()

        system_instruction = (
            "Eres un Arquitecto Cloud Experto y Diseñador Instruccional. "
            "Tu trabajo es analizar diagramas técnicos y extraer su conocimiento en formato de Flashcards (Anki). "
            "Responde ÚNICAMENTE con un JSON válido."
        )

        prompt = """
        Analiza el diagrama técnico adjunto. Extrae los componentes principales, 
        sus relaciones y su propósito. Devuelve un JSON estricto con la siguiente estructura:
        {
            "diagram_title": "Título inferido del diagrama",
            "summary": "Breve explicación de cómo fluye la información en este diagrama",
            "flashcards": [
                {
                    "front": "Pregunta sobre un componente específico del diagrama",
                    "back": "Respuesta detallada basada en la imagen",
                    "hint": "Pista didáctica"
                }
            ]
        }
        """

        parsed_data = await anyio.to_thread.run_sync(
            _analyze_diagram_sync,
            content_bytes,
            extension,
            prompt,
            system_instruction,
        )

        return {
            "status": "exito",
            "datos_diagrama": parsed_data,
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el análisis multimodal: {str(error)}"
        )
