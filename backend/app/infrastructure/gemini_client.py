"""
gemini_client.py

Purpose:
    Backward-compatibility shim. The real implementation lives in app.infrastructure.llm.gemini_client.
    Importing GeminiClient from this module still works transparently.
"""

from app.infrastructure.llm.gemini_client import GeminiClient  # noqa: F401

__all__ = ["GeminiClient"]
