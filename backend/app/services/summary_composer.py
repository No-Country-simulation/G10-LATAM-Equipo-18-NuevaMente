"""
summary_composer.py

Purpose:
    Builds the single continuous text used by the "Executive Summary" output
    format. Each generated block (key takeaway + business impact) becomes plain
    sentences grouped into paragraphs, so every consumer (API response, UI,
    PDF and Markdown exports) renders one flowing document instead of a list of
    separate numbered parts.

Input:
    - items (Iterable[Any]): generated summary blocks with "punto_clave" and
      "impacto_negocio" keys (raw dicts stored in AdaptedContent.items).

Output:
    - List[str]: paragraphs of plain prose, ready to join with blank lines.
"""

import re
from typing import Any, Iterable, List

# How many blocks (takeaway + impact) are merged into one paragraph.
ITEMS_PER_PARAGRAPH = 2

_SENTENCE_ENDINGS = ".!?"


def is_summary_item(item: Any) -> bool:
    """Return True when the item is an executive-summary block."""
    return isinstance(item, dict) and "punto_clave" in item


def is_summary_content(items: Iterable[Any]) -> bool:
    """Return True when every item is an executive-summary block."""
    items = list(items or [])
    return bool(items) and all(is_summary_item(it) for it in items)


def _finish(sentence: str) -> str:
    """Trim trailing whitespace and close the sentence with a period if needed."""
    sentence = sentence.strip()
    if sentence and sentence[-1] not in _SENTENCE_ENDINGS:
        sentence += "."
    return sentence


def compose_summary_paragraphs(items: Iterable[Any]) -> List[str]:
    """Turn summary blocks into paragraphs of plain prose (no headings or numbering)."""
    sentences: List[str] = []
    for item in items or []:
        if not is_summary_item(item):
            continue
        point = str(item.get("punto_clave") or "").strip().rstrip(".")
        impact = str(item.get("impacto_negocio") or "").strip()
        if point:
            point = point[0].upper() + point[1:]
        parts = [part for part in (_finish(point), _finish(impact)) if part]
        if parts:
            sentences.append(" ".join(parts))
    if not sentences:
        return []
    return [
        " ".join(sentences[i : i + ITEMS_PER_PARAGRAPH])
        for i in range(0, len(sentences), ITEMS_PER_PARAGRAPH)
    ]


def paragraphs_from_legacy_text(text: str) -> List[str]:
    """
    Normalize older stored summaries ("RESUMEN EJECUTIVO (N PUNTOS):" followed
    by "1. takeaway: impact" lines) into the same paragraph shape, so previous
    generations render as continuous prose too.
    """
    if not text:
        return []
    lines: List[str] = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^(resumen ejecutivo|executive summary)", line, re.IGNORECASE):
            continue
        lines.append(re.sub(r"^\d+\.\s*", "", line))
    if not lines:
        return []
    return [
        " ".join(lines[i : i + ITEMS_PER_PARAGRAPH])
        for i in range(0, len(lines), ITEMS_PER_PARAGRAPH)
    ]
