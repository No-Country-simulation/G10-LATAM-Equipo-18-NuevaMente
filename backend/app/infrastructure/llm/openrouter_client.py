"""
openrouter_client.py

Purpose:
    Implementation of BaseLLMClient for OpenRouter API (supporting Mistral, etc.).
    Adheres to the OpenAI-compatible chat completion specification.

Input:
    OPENROUTER_API_KEY environment variable.
    prompt, optional system_instruction, optional model identifier.

Output:
    Raw response strings or Pydantic validated models.
"""

import json
import logging
from typing import Any, Optional
import requests

from app.core.config import settings
from app.infrastructure.llm.base import BaseLLMClient

logger = logging.getLogger("OpenRouterClient")


class OpenRouterClient(BaseLLMClient):
    """OpenRouter client supporting Mistral and other models via unified BaseLLMClient interface."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.has_real_key = bool(
            self.api_key
            and self.api_key != "your_openrouter_api_key_here"
            and not self.api_key.startswith("mock")
        )
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_model = default_model or settings.DEFAULT_OPENROUTER_MODEL

    @property
    def is_available(self) -> bool:
        """True when OPENROUTER_API_KEY is configured."""
        return self.has_real_key

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Executes completion request against OpenRouter."""
        if not self.is_available:
            raise RuntimeError("OPENROUTER_API_KEY is not configured.")

        model = kwargs.get("model") or kwargs.get("model_name") or self.default_model
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        if json_output:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/No-Country-simulation/G10-LATAM-equipo-18-NuevaMente",
            "X-Title": "NuevaMente Educational Platform",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("OpenRouter generation failed with model %s: %s", model, exc)
            raise RuntimeError(f"OpenRouter API failure: {exc}") from exc
