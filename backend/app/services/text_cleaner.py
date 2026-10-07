"""
text_cleaner.py

Purpose:
    Central place for every text-cleaning rule applied during ingestion, so
    IngesterService and PdfParserService share one implementation.

    Two levels of cleaning:
    - Page level: remove_repeated_lines() strips running headers and footers
      that repeat across the pages of a PDF.
    - Text level: clean_text() / clean_title() normalize one section of text:
        1. Ligatures, non-breaking spaces and invisible characters.
        2. Explicit page-number lines ("Página 5 de 100", "- 7 -").
        3. Words split by a hyphen at the end of a line.
        4. Markdown emphasis markers (optional, for Markdown sources only).
        5. Repeated spaces and blank lines.
    Fenced code blocks are never modified by rules 2 to 5, and Markdown table
    rows only lose their trailing spaces. clean_text() is idempotent.

    Rules are conservative on purpose: technical text often contains values
    such as "temp > 80°C" or identifiers such as PART_NUMBER_A1, which must
    survive cleaning unchanged.

Input:
    - remove_repeated_lines(): a list with the text of each page.
    - clean_text() / clean_title(): a string, plus optional flags and a
      CleaningStats object that accumulates counters across calls.

Output:
    - Cleaned strings (or a list of cleaned pages).
    - CleaningStats: counters of what was changed, with summary() for logging.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, fields
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# A page line is treated as a running header/footer when it repeats on at
# least this share of the pages.
DEFAULT_MIN_REPETITION_RATIO = 0.4
_MIN_PAGES_FOR_REPEATED_LINES = 3

# Markdown structure that is never removed as a repeated line: headings,
# table rows, list items, block quotes, code fences and numbered items.
_MARKDOWN_STRUCTURE = re.compile(r"^(#{1,6}\s|\||[-*+]\s|>|```|\d+[.)]\s)")

# Ligatures become plain letters, non-breaking/thin spaces become a normal
# space, and soft hyphens and zero-width characters are dropped.
_CHARACTER_REPLACEMENTS = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
    "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
    "\u00a0": " ", "\u202f": " ", "\u2007": " ", "\u2009": " ",
    "\u00ad": "", "\u200b": "", "\u2060": "", "\ufeff": "",
}
_CHARACTER_TABLE = str.maketrans(_CHARACTER_REPLACEMENTS)

# Whole-line page numbering: "Página 5", "Page 5 of 10", "Pág. 3/8", "- 7 -".
# Marker lines such as "[PÁGINA 5]" do not match because of the brackets.
_PAGE_NUMBER_LINE = re.compile(
    r"^(?:(?:p[áa]gina|p[áa]g\.?|page)\s*\d+(?:\s*(?:de|of|/)\s*\d+)?|[-–—]\s*\d+\s*[-–—])$",
    re.IGNORECASE,
)

# A hyphen ending a line, preceded by a letter and followed by a line that
# starts in lowercase: the word was split by the page layout.
_LETTERS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_HYPHEN_LINE_BREAK = re.compile(rf"(?<=[{_LETTERS}])-[ \t]*\n[ \t]*(?=[a-záéíóúüñ])")

# Markdown markers. Emphasis only matches when the markers wrap a word and
# are not attached to other word characters, so identifiers such as
# PART_NUMBER_A1 or a * b * c are left alone.
_INLINE_CODE_SPLIT = re.compile(r"(`[^`\n]+`)")
_BOLD_STAR = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_BOLD_UNDERSCORE = re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)")
_ITALIC_STAR = re.compile(r"(?<![\w*])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![\w*])")
_ITALIC_UNDERSCORE = re.compile(r"(?<!\w)_(?=[^\s_])([^_\n]+?)(?<=[^\s_])_(?!\w)")
# A ">" at the start of a line is a quote marker unless a number or "="
# follows it, which is a comparison ("> 80°C", ">= 5").
_BLOCKQUOTE = re.compile(r"^([ \t]{0,3})>+(?![ \t]*[\d=])[ \t]?", re.MULTILINE)

_SPACES_RUN = re.compile(r"[ \t]+")
_BLANK_LINES_RUN = re.compile(r"\n{3,}")

_PDF_STREAM_PATTERN = re.compile(r"stream[\s\S]*?endstream", re.IGNORECASE)
_PDF_DICT_PATTERN = re.compile(r"<<[\s\S]*?>>")
_PDF_OBJ_PATTERN = re.compile(r"\d+\s+\d+\s+obj[\s\S]*?endobj", re.IGNORECASE)
_PDF_HEADER_FOOTER_PATTERN = re.compile(r"^.*(?:%PDF-|\b\d+\s+\d+\s+R\b|/FlateDecode|/Filter\b|/FontDescriptor\b|/MediaBox\b|/Parent\b|/Catalog\b|/Length\b).*$", re.MULTILINE | re.IGNORECASE)
_NON_PRINTABLE_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\uFFFD]")


def clean_pdf_binary_artifacts(text: str) -> str:
    """Removes raw PDF binary stream chunks, dictionary objects, and unprintable binary characters."""
    if not text:
        return ""
    text = _NON_PRINTABLE_CHARS.sub("", text)
    text = _PDF_STREAM_PATTERN.sub("", text)
    text = _PDF_DICT_PATTERN.sub("", text)
    text = _PDF_OBJ_PATTERN.sub("", text)
    text = _PDF_HEADER_FOOTER_PATTERN.sub("", text)
    return text



@dataclass
class CleaningStats:
    """Counters of what the cleaning rules changed."""
    characters_normalized: int = 0
    page_number_lines_removed: int = 0
    hyphenations_joined: int = 0
    markdown_markers_removed: int = 0
    repeated_lines_removed: int = 0

    def merge(self, other: "CleaningStats") -> None:
        """Adds the counters of another CleaningStats into this one."""
        for field in fields(self):
            setattr(self, field.name, getattr(self, field.name) + getattr(other, field.name))

    def summary(self) -> str:
        """Returns the non-zero counters as one log-friendly line."""
        parts = [f"{field.name}={getattr(self, field.name)}" for field in fields(self) if getattr(self, field.name)]
        return ", ".join(parts) if parts else "no changes"


# ---------------------------------------------------------------------------
# Page level
# ---------------------------------------------------------------------------

def remove_repeated_lines(
    pages: List[str],
    min_repetition_ratio: float = DEFAULT_MIN_REPETITION_RATIO,
    protect_markdown_structure: bool = False,
    stats: Optional[CleaningStats] = None,
) -> List[str]:
    """
    Strips lines that repeat across pages (running headers and footers).
    With protect_markdown_structure, headings, table rows, list items and
    similar lines are kept even when they repeat, so Markdown output is not
    damaged. Documents with fewer than 3 pages are returned unchanged.
    """
    if len(pages) < _MIN_PAGES_FOR_REPEATED_LINES:
        return pages

    # Each distinct line counts once per page, however often it appears in it.
    line_counts: Counter = Counter()
    for page in pages:
        line_counts.update({line.strip() for line in page.split("\n") if line.strip()})

    threshold = max(2, int(len(pages) * min_repetition_ratio))
    noisy_lines = {
        line for line, count in line_counts.items()
        if count >= threshold and not (protect_markdown_structure and _MARKDOWN_STRUCTURE.match(line))
    }

    cleaned_pages: List[str] = []
    removed = 0
    for page in pages:
        kept_lines = []
        for line in page.split("\n"):
            if line.strip() in noisy_lines:
                removed += 1
            else:
                kept_lines.append(line)
        cleaned_pages.append("\n".join(kept_lines))

    if stats is not None:
        stats.repeated_lines_removed += removed
    if removed:
        logger.info("Removed %d repeated header/footer lines (%d distinct).", removed, len(noisy_lines))

    return cleaned_pages


# ---------------------------------------------------------------------------
# Text level
# ---------------------------------------------------------------------------

def clean_text(
    text: str,
    strip_markdown: bool = False,
    stats: Optional[CleaningStats] = None,
) -> str:
    """
    Applies the text-level rules to one piece of text and returns it stripped
    at both ends. strip_markdown removes emphasis, inline-code and quote
    markers; leave it off for plain-text sources where "*" and "_" are content.
    """
    if not text:
        return ""

    local_stats = stats if stats is not None else CleaningStats()

    text = clean_pdf_binary_artifacts(text)
    text = _normalize_characters(text, local_stats)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Code blocks pass through untouched; only prose segments are cleaned.
    cleaned_segments = []
    for is_code, segment in _split_code_fences(text):
        if is_code:
            cleaned_segments.append(segment)
        else:
            cleaned_segments.append(_clean_prose_segment(segment, strip_markdown, local_stats))

    return "\n".join(cleaned_segments).strip()


def clean_title(title: str, stats: Optional[CleaningStats] = None, strip_markdown: bool = True) -> str:
    """
    Cleans a section title with the same rules as the body and collapses it
    to a single line. Returns "" when nothing is left.
    """
    cleaned = clean_text(title, strip_markdown=strip_markdown, stats=stats)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_characters(text: str, stats: CleaningStats) -> str:
    """Replaces ligatures and special spaces, and drops invisible characters."""
    stats.characters_normalized += sum(text.count(char) for char in _CHARACTER_REPLACEMENTS)
    return text.translate(_CHARACTER_TABLE)


def _split_code_fences(text: str) -> List[Tuple[bool, str]]:
    """
    Splits text into consecutive (is_code, segment) pairs, where code segments
    are fenced blocks including their fence lines. Joining the segments with
    "\\n" rebuilds the original text. An unclosed fence runs to the end.
    """
    segments: List[Tuple[bool, str]] = []
    current: List[str] = []
    in_code = False

    for line in text.split("\n"):
        is_fence = line.lstrip().startswith("```")
        if is_fence and not in_code:
            if current:
                segments.append((False, "\n".join(current)))
            current = [line]
            in_code = True
        elif is_fence and in_code:
            current.append(line)
            segments.append((True, "\n".join(current)))
            current = []
            in_code = False
        else:
            current.append(line)

    if current:
        segments.append((in_code, "\n".join(current)))
    return segments


def _clean_prose_segment(segment: str, strip_markdown: bool, stats: CleaningStats) -> str:
    """Applies rules 2 to 5 (page numbers, hyphenation, Markdown, whitespace) to a non-code segment."""
    segment = _remove_page_number_lines(segment, stats)
    segment = _join_hyphenated_lines(segment, stats)
    if strip_markdown:
        segment = _strip_markdown_markers(segment, stats)
    return _collapse_whitespace(segment)


def _remove_page_number_lines(segment: str, stats: CleaningStats) -> str:
    """Drops lines that only contain explicit page numbering."""
    kept_lines = []
    for line in segment.split("\n"):
        if _PAGE_NUMBER_LINE.match(line.strip()):
            stats.page_number_lines_removed += 1
        else:
            kept_lines.append(line)
    return "\n".join(kept_lines)


def _join_hyphenated_lines(segment: str, stats: CleaningStats) -> str:
    """Rejoins words split by a hyphen at the end of a line."""
    segment, count = _HYPHEN_LINE_BREAK.subn("", segment)
    stats.hyphenations_joined += count
    return segment


def _strip_markdown_markers(segment: str, stats: CleaningStats) -> str:
    """
    Removes quote markers, bold/italic markers and inline-code backticks,
    keeping the text they wrap. Text inside inline code is kept exactly as
    written, so identifiers such as __init__ are not mistaken for bold.
    """
    segment, removed = _BLOCKQUOTE.subn(r"\1", segment)

    # Splitting on inline code puts code spans at odd positions.
    parts = _INLINE_CODE_SPLIT.split(segment)
    for index, part in enumerate(parts):
        if index % 2 == 1:
            parts[index] = part[1:-1]
            removed += 1
            continue
        for pattern in (_BOLD_STAR, _BOLD_UNDERSCORE, _ITALIC_STAR, _ITALIC_UNDERSCORE):
            part, count = pattern.subn(r"\1", part)
            removed += count
        parts[index] = part

    stats.markdown_markers_removed += removed
    return "".join(parts)


def _collapse_whitespace(segment: str) -> str:
    """
    Collapses repeated spaces inside lines and limits blank lines to one.
    Leading indentation is kept, and table rows only lose trailing spaces.
    """
    lines = []
    for line in segment.split("\n"):
        if line.lstrip().startswith("|"):
            lines.append(line.rstrip())
            continue
        indentation = line[: len(line) - len(line.lstrip())]
        body = _SPACES_RUN.sub(" ", line.strip())
        lines.append(indentation + body if body else "")
    return _BLANK_LINES_RUN.sub("\n\n", "\n".join(lines))