"""
groq_adapter.py

Purpose:
    Backward-compatibility shim. GroqAdapter is now GroqClient in app.infrastructure.llm.groq_client.
    This file preserves the original import path for any references that were not migrated.
"""

from app.infrastructure.llm.groq_client import GroqClient as GroqAdapter  # noqa: F401

__all__ = ["GroqAdapter"]
