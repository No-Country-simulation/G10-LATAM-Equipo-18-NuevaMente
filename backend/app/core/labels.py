"""
labels.py

Purpose:
    Maps internal domain keys (defined in English) to human-readable
    Spanish labels displayed in the user interface, and resolves the target
    output language (Spanish / English / Portuguese) into a stable code used
    by prompts and by every generated message.

Input:
    None (static dictionaries), plus the raw language value that arrives with
    the adaptation request (e.g. "es", "en", "pt", "Spanish", "Portuguese").

Output:
    Dictionaries: PROFILE_LABELS_ES, FORMAT_LABELS_ES, NICHE_LABELS_ES.
    Functions: resolve_language_code, language_display_name, is_language,
    canonical_format_key, summary_message.
"""

from typing import Any, Optional

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


# ---------------------------------------------------------------------------
# Target language resolution (never hardcoded to a single language)
# ---------------------------------------------------------------------------

LANGUAGE_NAMES = {
    "es": "Spanish",
    "en": "English",
    "pt": "Portuguese",
}

_LANGUAGE_ALIASES = {
    "es": "es", "spa": "es", "spanish": "es", "español": "es", "espanol": "es",
    "castellano": "es", "es-419": "es",
    "en": "en", "eng": "en", "english": "en", "inglés": "en", "ingles": "en",
    "pt": "pt", "por": "pt", "portuguese": "pt", "portugués": "pt", "portugues": "pt",
    "br": "pt", "pt-br": "pt",
}

# ---------------------------------------------------------------------------
# Canonical output-format keys
# ---------------------------------------------------------------------------

FORMAT_CANONICAL_KEYS = {
    "flashcards": "flashcards",
    "flashcard": "flashcards",
    "tarjetas": "flashcards",
    "quiz": "quiz",
    "cuestionario": "quiz",
    "cuestionarios": "quiz",
    "tutorial": "tutorial",
    "guia practica": "tutorial",
    "guía práctica": "tutorial",
    "resumen ejecutivo": "executive_summary",
    "resumen": "executive_summary",
    "executive summary": "executive_summary",
    "executive_summary": "executive_summary",
    "tldr": "executive_summary",
    "guion de clase": "class_script",
    "guion": "class_script",
    "class script": "class_script",
    "class_script": "class_script",
}

# ---------------------------------------------------------------------------
# Executive summary messages (per target language)
# ---------------------------------------------------------------------------

SUMMARY_MESSAGES = {
    "es": {
        "sources_header": "Fuentes",
        "empty_detail": (
            "No se pudo generar un resumen con el contenido disponible en este documento. "
            "Verifica que el documento tenga texto suficiente e inténtalo de nuevo."
        ),
        "empty_short": "No se pudo generar el resumen.",
        "partial": "El documento admite {generated} párrafos de los {requested} solicitados.",
        "generic_source": "Documento completo",
        "page_prefix": "p.",
    },
    "en": {
        "sources_header": "Sources",
        "empty_detail": (
            "The executive summary could not be generated from the content available in this "
            "document. Make sure the document contains enough text and try again."
        ),
        "empty_short": "The executive summary could not be generated.",
        "partial": "The document supports {generated} paragraphs out of the {requested} requested.",
        "generic_source": "Full document",
        "page_prefix": "p.",
    },
    "pt": {
        "sources_header": "Fontes",
        "empty_detail": (
            "Não foi possível gerar um resumo com o conteúdo disponível neste documento. "
            "Verifique se o documento tem texto suficiente e tente novamente."
        ),
        "empty_short": "Não foi possível gerar o resumo.",
        "partial": "O documento admite {generated} parágrafos dos {requested} solicitados.",
        "generic_source": "Documento completo",
        "page_prefix": "p.",
    },
}


def resolve_language_code(raw: Optional[str]) -> str:
    """
    Normalizes any language label coming from the request into a supported
    code ("es", "en", "pt"). Falls back to the configured default language.
    """
    default_code = _LANGUAGE_ALIASES.get(
        str(settings.DEFAULT_OUTPUT_LANGUAGE or "").strip().lower(), "es"
    )
    if not raw:
        return default_code
    value = str(raw).strip().lower()
    if value in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[value]
    head = value.replace("_", "-").split("-")[0]
    return _LANGUAGE_ALIASES.get(head, default_code)


def language_display_name(raw: Optional[str]) -> str:
    """Returns the English language name used inside LLM prompts."""
    return LANGUAGE_NAMES[resolve_language_code(raw)]


def is_language(raw: Optional[str], language: Optional[str]) -> bool:
    """True when both values resolve to the same target language code."""
    return resolve_language_code(raw) == resolve_language_code(language)


def canonical_format_key(raw: Optional[str]) -> str:
    """
    Normalizes an output format label ("Resumen Ejecutivo", "resumen", ...) into
    a canonical key ("executive_summary", "flashcards", ...) used to look up
    prompt templates, model cascades and format-specific behaviour.
    """
    if not raw:
        return "flashcards"
    value = str(raw).strip().lower()
    if value in FORMAT_CANONICAL_KEYS:
        return FORMAT_CANONICAL_KEYS[value]
    for key, canonical in FORMAT_CANONICAL_KEYS.items():
        if key in value:
            return canonical
    return value


def summary_message(key: str, language: Optional[str] = "Spanish", **kwargs: Any) -> str:
    """Returns an executive-summary message written in the target language."""
    code = resolve_language_code(language)
    messages = SUMMARY_MESSAGES.get(code, SUMMARY_MESSAGES["es"])
    template = messages.get(key, messages["empty_detail"])
    return template.format(**kwargs) if kwargs else template


def get_capacity_warning(effective_count: int, requested_count: int, language: str = "Spanish") -> str:
    """Generates warning message in target language when document density limits generation target."""
    code = resolve_language_code(language)
    if code == "es":
        return get_capacity_warning_es(effective_count, requested_count)
    if code == "pt":
        return (
            f"Seu documento suportou {effective_count} itens verificados. "
            f"Com um documento mais extenso você poderá gerar os {requested_count} solicitados."
        )
    return (
        f"Your document supported {effective_count} verified items. "
        f"With a longer document you can generate the {requested_count} requested items."
    )


def get_contextualized_intro(
    doc_title: str, effective_count: int, recipient_profile: str, niche: str, language: str = "Spanish"
) -> str:
    """Builds a contextualized introduction in the target language."""
    code = resolve_language_code(language)
    prof_label = PROFILE_LABELS_ES.get(recipient_profile, recipient_profile)
    niche_label = NICHE_LABELS_ES.get(niche, niche)
    if code == "es":
        return (
            f"Versión didáctica adaptada de «{doc_title}» estructurada en {effective_count} elementos clave "
            f"para el perfil '{prof_label}' orientada al sector '{niche_label}'."
        )
    if code == "pt":
        return (
            f"Versão didática adaptada de «{doc_title}» estruturada em {effective_count} elementos-chave "
            f"para o perfil '{prof_label}' orientada ao setor '{niche_label}'."
        )
    return (
        f"Adapted version of '{doc_title}' structured into {effective_count} elements "
        f"for profile '{recipient_profile}' in the '{niche}' sector."
    )

