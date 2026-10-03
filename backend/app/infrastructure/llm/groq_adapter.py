import json
from typing import Type, TypeVar, Any
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel
import groq
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

logger.add("logs/llm_agents_{time}.log", rotation="10 MB", level="DEBUG")

class GroqAdapter:
    """
    Adapter para Groq que maneja resiliencia (rate limits, timeouts) y
    salidas estructuradas estrictas usando Pydantic.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = groq.Client(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1.5, min=2, max=15),
        retry=retry_if_exception_type((groq.APIConnectionError, groq.RateLimitError, groq.InternalServerError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Fallo temporal con Groq. Reintentando en {retry_state.next_action.sleep} segundos. Intento {retry_state.attempt_number}/4"
        )
    )
    def generate_structured(self, prompt: str, schema: Type[T], model: str = "openai/gpt-oss-20b") -> T:
        """
        Genera una salida estructurada asegurando que cumpla con el modelo de Pydantic.
        """
        try:
            logger.info(f"Llamando a Groq ({model}) para salida estructurada: {schema.__name__}")
            
            # Formatear el esquema para dárselo al LLM
            schema_json = schema.model_json_schema()
            
            messages = [
                {
                    "role": "system", 
                    "content": f"You are an API that exclusively returns JSON. Respond EXACTLY matching this JSON schema:\n{json.dumps(schema_json, indent=2)}\nDO NOT include any markdown code blocks, explanations, or text outside the JSON."
                },
                {"role": "user", "content": prompt}
            ]

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            raw_content = response.choices[0].message.content
            logger.debug("Respuesta generada, validando con Pydantic...")
            
            # Pydantic validará automáticamente y lanzará ValidationError si el LLM alucinó campos
            validated_data = schema.model_validate_json(raw_content)
            logger.success(f"Salida estructurada validada con éxito: {schema.__name__}")
            return validated_data
            
        except Exception as e:
            logger.error(f"Error en generate_structured: {str(e)}")
            raise
