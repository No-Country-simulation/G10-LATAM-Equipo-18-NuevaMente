"""
summary_composer.py

Purpose:
    Builds the single continuous text used by the "Executive Summary" output
    format. Each generated block (key takeaway + business impact) becomes plain
    sentences grouped into paragraphs, so every consumer (API response, UI,
    PDF and Markdown exports) renders one flowing document instead of a list of
    separate numbered parts.

    The final text also carries a short reference list: every paragraph ends
    with the numbers of the sections it is based on, and the numbers are
    resolved once at the end against the document title, section and page.

Input:
    - items (Iterable[Any]): generated summary blocks with "punto_clave" and
      "impacto_negocio" keys (raw dicts stored in AdaptedContent.items).

Output:
    - List[str]: paragraphs of plain prose, ready to join with blank lines.
    - str: the full summary text (paragraphs + reference list).
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.labels import summary_message

# How many blocks (takeaway + impact) are merged into one paragraph.
ITEMS_PER_PARAGRAPH = 1

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


def _block_sentence(item: Any) -> str:
    """Turns one summary block into a single plain sentence."""
    point = str(item.get("punto_clave") or "").strip().rstrip(".")
    impact = str(item.get("impacto_negocio") or "").strip()
    if point:
        point = point[0].upper() + point[1:]
    parts = [part for part in (_finish(point), _finish(impact)) if part]
    return " ".join(parts)


def compose_summary_paragraphs(items: Iterable[Any]) -> List[str]:
    """Turn summary blocks into paragraphs of plain prose (no headings or numbering)."""
    sentences: List[str] = []
    for item in items or []:
        if not is_summary_item(item):
            continue
        sentence = _block_sentence(item)
        if sentence:
            sentences.append(sentence)
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


# ---------------------------------------------------------------------------
# Reference list (citations) for the executive summary
# ---------------------------------------------------------------------------

def _clean_section(value: Any) -> str:
    """Normalizes a section label so equivalent labels share the same entry."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text.strip(" .:-—")


def _source_pages(source: Dict[str, Any]) -> List[int]:
    """Collects the page numbers declared by a source (supports lists)."""
    pages: List[int] = []
    raw = source.get("pagina") if isinstance(source, dict) else None
    if isinstance(raw, bool):
        raw = None
    if isinstance(raw, int) and raw > 0:
        pages.append(raw)
    elif isinstance(raw, (list, tuple, set)):
        for item in raw:
            if isinstance(item, int) and not isinstance(item, bool) and item > 0:
                pages.append(item)
    return sorted(set(pages))


def _source_section(source: Dict[str, Any], generic_label: str) -> str:
    """Returns the section label of a source, falling back to its breadcrumb."""
    section = _clean_section(source.get("seccion"))
    if section:
        return section
    breadcrumb = str(source.get("breadcrumb") or "").strip()
    if breadcrumb:
        tail = [part for part in re.split(r"[>|]", breadcrumb) if part.strip()]
        if tail:
            return _clean_section(tail[-1])
    return ""


def _source_key(section: str, pages: Tuple[int, ...]) -> Tuple[str, Tuple[int, ...]]:
    """Key that identifies a reference entry: same section and same pages."""
    return (section.lower(), pages)


def compose_summary_with_citations(
    items: Iterable[Any],
    doc_title: str,
    target_language: str = "Spanish",
) -> str:
    """
    Builds the final executive summary text.

    Every paragraph ends with the reference numbers of the sections it is
    based on ("[1]", "[2][4]"). The same number may appear in several
    paragraphs. At the end, the document title is printed once as the general
    source, followed by one line per reference number with its section and
    page, when known.

    Returns an empty string when there is nothing to show, so the caller can
    display the "could not be generated" message instead.
    """
    generic_label = summary_message("generic_source", target_language)
    page_prefix = summary_message("page_prefix", target_language)

    entries: List[Dict[str, Any]] = []
    entries_by_key: Dict[Tuple[str, Tuple[int, ...]], Dict[str, Any]] = {}
    paragraphs: List[str] = []

    for item in items or []:
        if not is_summary_item(item):
            continue
        sentence = _block_sentence(item)
        if not sentence:
            continue

        numbers: List[int] = []
        for source in item.get("fuentes") or []:
            if not isinstance(source, dict):
                continue
            section = _source_section(source, generic_label)
            pages = _source_pages(source)
            if not section and not pages:
                # Nothing identifying this source: it cannot be referenced.
                continue
            key = _source_key(section, tuple(pages))
            entry = entries_by_key.get(key)
            if entry is None:
                entry = {
                    "number": len(entries) + 1,
                    "section": section or generic_label,
                    "pages": list(pages),
                }
                entries_by_key[key] = entry
                entries.append(entry)
            elif pages and not entry["pages"]:
                entry["pages"] = list(pages)
            if entry["number"] not in numbers:
                numbers.append(entry["number"])

        if numbers:
            markers = "".join(f"[{number}]" for number in sorted(numbers))
            sentence = f"{sentence} {markers}"
        paragraphs.append(sentence)

    if not paragraphs:
        return ""

    body = "\n\n".join(paragraphs)

    if not entries:
        return body

    header = summary_message("sources_header", target_language)
    lines: List[str] = [header]
    title = str(doc_title or "").strip()
    if title:
        lines.append(title)
    for entry in entries:
        label = entry["section"]
        pages = entry["pages"]
        if pages:
            page_text = ", ".join(f"{page_prefix} {page}" for page in pages)
            label = f"{label} ({page_text})"
        lines.append(f"[{entry['number']}] {label}")

    return f"{body}\n\n" + "\n".join(lines)


def split_summary_text(text: str) -> Tuple[List[str], List[str]]:
    """
    Splits a stored executive summary into its paragraphs and the lines of its
    reference list (header, general source and one line per reference number).
    """
    if not text:
        return [], []
    lines = str(text).splitlines()
    header_index = -1
    for index, line in enumerate(lines):
        if line.strip().lower() in ("fuentes", "sources", "fontes"):
            header_index = index
            break

    body_lines = lines[:header_index] if header_index >= 0 else lines
    body = [line.strip() for line in body_lines if line.strip()]
    references = [line.strip() for line in lines[header_index:] if line.strip()] if header_index >= 0 else []
    return body, references
