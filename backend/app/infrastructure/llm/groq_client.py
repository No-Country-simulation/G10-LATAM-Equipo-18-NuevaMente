"""
groq_client.py

Purpose:
    Implementation of BaseLLMClient for Groq LPU with automatic retries via Tenacity.
    Unifies resilience against rate-limits/connection drops and supports Pydantic structured output.

Input:
    GROQ_API_KEY environment variable.
    prompt, optional system_instruction, optional model name.

Output:
    Raw response strings or Pydantic validated models.
"""

import json
import logging
from typing import Any, Optional, Type
import groq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.infrastructure.llm.base import BaseLLMClient, T

logger = logging.getLogger("GroqClient")


class GroqClient(BaseLLMClient):
    """Groq API client implementing BaseLLMClient with built-in retry resilience."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.has_real_key = bool(
            self.api_key
            and self.api_key != "your_groq_api_key_here"
            and self.api_key != "mock_key"
        )
        self._client: Optional[groq.Client] = None

        if self.has_real_key:
            try:
                self._client = groq.Client(api_key=self.api_key)
                logger.info("Groq client initialized successfully.")
            except Exception as exc:
                logger.warning("Failed to initialize Groq client: %s", exc)
                self.has_real_key = False
        else:
            logger.info("Groq client mock/inactive mode (no key configured).")

    @property
    def is_available(self) -> bool:
        """True when a valid Groq client instance is present."""
        return self.has_real_key and self._client is not None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.2, min=1.5, max=10),
        retry=retry_if_exception_type((groq.APIConnectionError, groq.RateLimitError, groq.InternalServerError)),
        before_sleep=lambda retry_state: logger.warning(
            "Groq temporary failure. Retrying in %.2fs (attempt %d/3)...",
            retry_state.next_action.sleep,
            retry_state.attempt_number,
        ),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Generates completion with Groq with exponential backoff on transient errors."""
        if not self.is_available:
            raise RuntimeError("GROQ_API_KEY is not configured or client is unavailable.")

        model = kwargs.get("model") or kwargs.get("model_name") or settings.DEFAULT_GROQ_MODEL
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response_format = {"type": "json_object"} if json_output else None

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
            temperature=kwargs.get("temperature", 0.2),
        )
        return response.choices[0].message.content

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        json_output: bool = True,
    ) -> str:
        """Backward compatibility helper matching the original generate_content signature."""
        return self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            json_output=json_output,
            model=model_name or settings.DEFAULT_GROQ_MODEL,
        )


# Backward compatibility alias for any component expecting GroqAdapter
GroqAdapter = GroqClient
