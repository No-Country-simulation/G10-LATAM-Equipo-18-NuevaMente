import tempfile
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.infrastructure.llm import GeminiClient
from app.core.config import settings
import json

router = APIRouter()
gemini_client = GeminiClient()

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
        
        # Escribir temporalmente la imagen
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_file.write(content_bytes)
            temp_path = temp_file.name

        try:
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
            
            raw_response = gemini_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                model_name="gemini-2.5-flash",
                json_output=True,
                image_path=temp_path
            )
            
            raw_response = raw_response.strip().removeprefix("```json").removesuffix("```").strip()
            parsed_data = json.loads(raw_response)
            
            return {
                "status": "exito",
                "datos_diagrama": parsed_data
            }
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el análisis multimodal: {str(error)}"
        )
