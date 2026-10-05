"""
base.py

Purpose:
    Abstract base class defining the unified contract for LLM generation clients.
    Standardizes text generation, structured JSON generation with Pydantic,
    and provider availability checks across Gemini, Groq, OpenRouter, and local fallbacks.

Input:
    Prompts, optional system instructions, and Pydantic schema types.

Output:
    Raw response strings or strongly validated Pydantic model instances.
"""

from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    """Abstract base contract for all LLM providers in NuevaMente."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Indicates whether this client has a valid credential configured."""
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Executes text or raw JSON generation against the LLM provider.

        Args:
            prompt: User/task instructions.
            system_instruction: Optional system-level prompt guiding style/role.
            json_output: Whether to instruct the model to respond strictly in JSON.
            **kwargs: Provider-specific generation parameters (e.g. image_path, temperature).

        Returns:
            The raw text/JSON response from the provider.
        """
        raise NotImplementedError

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        """
        Generates content and guarantees validation against a target Pydantic schema.

        Args:
            prompt: User/task instructions.
            schema: Pydantic model class to validate and instantiate.
            system_instruction: Optional system-level prompt.
            **kwargs: Extra parameters passed to generate().

        Returns:
            An instance of schema (T) containing validated data.

        Raises:
            ValidationError: If model output does not conform to the schema.
            RuntimeError: If raw generation fails.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        schema_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Output must strictly conform to this JSON Schema:\n{schema_json}\n"
            "Return valid JSON only. Do not add markdown wrapping or introductory text."
        )

        sys_inst = system_instruction or "You are an API that strictly returns valid JSON matching requested schemas."

        raw = self.generate(prompt=schema_prompt, system_instruction=sys_inst, json_output=True, **kwargs)
        cleaned = self._clean_json_string(raw)
        return schema.model_validate_json(cleaned)

    @staticmethod
    def _clean_json_string(raw: str) -> str:
        """Strips markdown code fences, trailing commas, or extraneous whitespace."""
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
