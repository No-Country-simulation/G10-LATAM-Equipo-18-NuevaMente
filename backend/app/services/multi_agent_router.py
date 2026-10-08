"""
multi_agent_router.py

Purpose:
    Intelligent router and provider order strategy for educational content adaptation.
    Routes tasks to the most suitable LLM provider (Groq, Gemini, OpenRouter) based on
    the requested pedagogical format and content requirements, while defining an
    optimized cascade order for resilient fallbacks.

Inputs:
    - output_format (str): Educational output format (flashcards, quiz, tutorial, etc.)
    - task_description (str, optional): Additional context or user instructions.

Outputs:
    - preferred_provider (str): Name of primary LLM provider ('groq', 'gemini', 'openrouter').
    - provider_cascade (List[str]): Ordered list of provider identifiers for fallback execution.
"""

from typing import Dict, List, Optional


class AgentProfile:
    """Represents a supported LLM provider and its pedagogical specialization."""

    def __init__(self, key: str, name: str, description: str, formats: List[str]):
        self.key = key.lower()
        self.name = name
        self.description = description
        self.formats = [f.lower() for f in formats]


class MultiAgentRouter:
    """
    Intelligent router and cascade strategy manager.
    Selects primary provider and constructs prioritized fallback order based on format.
    """

    def __init__(self):
        # Supported active providers in the platform
        self.providers: Dict[str, AgentProfile] = {
            "groq": AgentProfile(
                key="groq",
                name="GROQ",
                description="Ultra-fast generation for highly structured formats (Flashcards, Quizzes).",
                formats=["flashcards", "flashcard", "quiz", "cuestionario"],
            ),
            "gemini": AgentProfile(
                key="gemini",
                name="GEMINI",
                description="Deep reasoning and extensive context for instructional tutorials and deep dives.",
                formats=["tutorial", "guía práctica", "guia practica", "investigacion", "deep_research"],
            ),
            "openrouter": AgentProfile(
                key="openrouter",
                name="OPENROUTER",
                description="Versatile open-weights models (Mistral) optimal for executive summaries and class scripts.",
                formats=["resumen ejecutivo", "resumen", "executive_summary", "guion de clase", "guion", "script"],
            ),
        }

        # Optimized fallback cascade by format
        # E.g. Flashcards: Groq (ultra fast) -> Gemini (fallback) -> OpenRouter (secondary fallback)
        self._format_cascade_map: Dict[str, List[str]] = {
            "flashcards": ["groq", "gemini", "openrouter"],
            "flashcard": ["groq", "gemini", "openrouter"],
            "quiz": ["groq", "gemini", "openrouter"],
            "tutorial": ["gemini", "openrouter", "groq"],
            "resumen ejecutivo": ["openrouter", "groq", "gemini"],
            "resumen": ["openrouter", "groq", "gemini"],
            "executive_summary": ["openrouter", "groq", "gemini"],
            "guion de clase": ["openrouter", "gemini", "groq"],
            "guion": ["openrouter", "gemini", "groq"],
            "class_script": ["openrouter", "gemini", "groq"],
        }

    def register_provider(self, key: str, name: str, description: str, formats: List[str]) -> None:
        """Enables easy extension with new LLM providers (e.g. Ollama, Cerebras, DeepSeek)."""
        self.providers[key.lower()] = AgentProfile(
            key=key,
            name=name,
            description=description,
            formats=formats,
        )

    def route_task(self, output_format: str, task_description: str = "") -> str:
        """
        Returns the preferred primary LLM provider key ('groq', 'gemini', 'openrouter').
        """
        fmt = (output_format or "").lower().strip()
        desc = (task_description or "").lower()

        for key, profile in self.providers.items():
            for f in profile.formats:
                if f in fmt or f in desc:
                    return key

        return "gemini"

    def get_cascade_order(self, output_format: str) -> List[str]:
        """
        Returns an ordered list of provider keys for the fallback cascade.
        """
        fmt = (output_format or "").lower().strip()
        for key, cascade in self._format_cascade_map.items():
            if key in fmt:
                return list(cascade)

        # Default fallback cascade
        return ["gemini", "groq", "openrouter"]

