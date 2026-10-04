"""
gemini_client.py

Purpose:
    Implementation of BaseLLMClient for Google Gemini (google-genai SDK v2.x).
    Supports multimodal input (images) and structured JSON generation.

Input:
    GEMINI_API_KEY environment variable.
    prompt, optional system_instruction, optional image_path.

Output:
    Raw response strings or Pydantic validated models.
"""

import logging
import os
from typing import Any, Optional

from app.core.config import settings
from app.infrastructure.llm.base import BaseLLMClient

logger = logging.getLogger("GeminiClient")


class GeminiClient(BaseLLMClient):
    """Google Gemini LLM client implementing the unified BaseLLMClient interface."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.has_real_key = bool(
            self.api_key
            and self.api_key != "MOCK_GEMINI_KEY"
            and self.api_key != "your_gemini_api_key_here"
        )
        self._client = None

        if self.has_real_key:
            try:
                import httpx  # noqa: PLC0415
                from google import genai  # noqa: PLC0415
                from google.genai import types  # noqa: PLC0415

                # Bypass SSL verification on environments with custom local CA certs
                httpx_client = httpx.Client(verify=False)
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(httpx_client=httpx_client),
                )
                logger.info("Google Gemini SDK (google-genai v2) configured successfully.")
            except Exception as exc:
                logger.warning("Failed to initialize Gemini SDK: %s. Entering fallback mode.", exc)
                self.has_real_key = False
        else:
            logger.info("Gemini mock/inactive mode (no valid API key found).")

    @property
    def is_available(self) -> bool:
        """True when Gemini client was successfully initialized with a valid API key."""
        return self.has_real_key and self._client is not None

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Executes text or multimodal generation using the chat session API."""
        if not self.is_available:
            raise RuntimeError("GEMINI_API_KEY is not configured or client failed to initialize.")

        from google.genai import types  # noqa: PLC0415

        model_name = kwargs.get("model_name") or settings.GEMINI_LLM_MODEL
        image_path = kwargs.get("image_path")

        # Build generation config
        gen_config_kwargs = {}
        if json_output:
            gen_config_kwargs["response_mime_type"] = "application/json"

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **gen_config_kwargs,
        ) if system_instruction or gen_config_kwargs else None

        # Build message parts - text first, then optional image
        if image_path and os.path.exists(image_path):
            import mimetypes  # noqa: PLC0415
            mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            message_parts = [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ]
        else:
            message_parts = prompt

        try:
            chat = self._client.chats.create(model=model_name, config=gen_config)
            response = chat.send_message(message_parts)
            return response.text
        except Exception as exc:
            logger.warning("Gemini generation failed: %s", exc)
            raise RuntimeError(f"Gemini API failure: {exc}") from exc


    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        json_output: bool = True,
        image_path: Optional[str] = None,
    ) -> str:
        """Backward compatibility helper matching the original generate_content signature."""
        return self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            json_output=json_output,
            model_name=model_name,
            image_path=image_path,
        )
