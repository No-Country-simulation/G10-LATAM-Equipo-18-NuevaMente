"""
labels.py

Purpose:
    Maps internal domain keys (defined in English) to human-readable
    Spanish labels displayed in the user interface.

Input:
    None (static dictionaries).

Output:
    Dictionaries: PROFILE_LABELS_ES, FORMAT_LABELS_ES, NICHE_LABELS_ES.
"""

from app.core.config import settings

PROFILE_LABELS_ES = {
    settings.PROFILE_BEGINNER: "Principiante / Transición de Carrera",
    settings.PROFILE_JUNIOR_DEV: "Desarrollador Junior / Semi Senior",
    settings.PROFILE_TECH_LEAD: "Líder Técnico / Arquitecto",
    settings.PROFILE_EXECUTIVE: "Gestor / Ejecutivo (No Técnico)",
}

FORMAT_LABELS_ES = {
    settings.FORMAT_TUTORIAL: "Guía Práctica Paso a Paso",
    settings.FORMAT_FLASHCARDS: "Flashcards de Memorización",
    settings.FORMAT_QUIZ: "Quiz Interactivo con Justificaciones",
    settings.FORMAT_SUMMARY: "Resumen Ejecutivo (TL;DR)",
    settings.FORMAT_CLASS_SCRIPT: "Guion de Clase / Video",
}

NICHE_LABELS_ES = {
    settings.NICHE_GENERAL: "General",
    settings.NICHE_FINTECH: "Fintech",
    settings.NICHE_HEALTH: "Salud",
    settings.NICHE_ECOMMERCE: "E-commerce",
}

TITLE_TEMPLATES_ES = {
    settings.FORMAT_FLASHCARDS: "Mazo de Flashcards ({count} Tarjetas): {doc_title}",
    settings.FORMAT_QUIZ: "Evaluación Técnica Interactiva ({count} Preguntas): {doc_title}",
    settings.FORMAT_TUTORIAL: "Tutorial Paso a Paso ({count} Módulos): {doc_title}",
    settings.FORMAT_SUMMARY: "Resumen Ejecutivo (TL;DR - {count} Puntos): {doc_title}",
    settings.FORMAT_CLASS_SCRIPT: "Guion de Clase Didáctica ({count} Escenas): {doc_title}",
}

def get_capacity_warning_es(effective_count: int, requested_count: int) -> str:
    """Generates Spanish warning message when document density limits the generation target."""
    return (
        f"Tu documento dio para {effective_count} elementos verificados. "
        f"Con un documento más extenso podrás generar los {requested_count} solicitados."
    )

