"""
groq_client.py

Purpose:
    Backward-compatibility shim. The real implementation lives in app.infrastructure.llm.groq_client.
    Importing GroqClient from this module still works transparently.
"""

from app.infrastructure.llm.groq_client import GroqClient  # noqa: F401

__all__ = ["GroqClient"]
