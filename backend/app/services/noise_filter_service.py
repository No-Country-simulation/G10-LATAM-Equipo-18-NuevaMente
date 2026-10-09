"""
noise_filter_service.py

Purpose:
    Detects and discards sections that carry no technical value before they
    are chunked and embedded, because their generic wording makes the RAG
    retrieve them for unrelated queries. Five categories:
        legal              covers, copyright and legal notices, disclaimers.
        revision_history   revision tables and change logs.
        index_lists        tables of contents and lists of tables/figures.
        near_empty         chapter dividers and blank pages.
        normative_appendix certification, conformity and compliance appendices.

    Detection works on each section's title and content, using regular
    expressions loaded from a JSON file (settings.NOISE_PATTERNS_FILE). Any
    pattern list missing from that file falls back to the built-in default,
    so the file may hold only the lists the user wants to override.

    Safeguards: short safety notices are never treated as near-empty; a
    revision table is only detected by content when it is not a long section;
    the filter is skipped (with a warning) when it would discard more than
    settings.NOISE_MAX_DISCARD_RATIO of the text or every section; and a dry
    run reports what would be discarded without discarding anything.

Input:
    - sections: objects with `title`, `content` and `page_number` attributes
      (IngesterService's Section dataclass), already cleaned by text_cleaner.
    - categories (optional): restricts the filter to some categories.
    - dry_run (bool): report only, discard nothing.

Output:
    - (kept_sections, NoiseReport): the sections to keep, in their original
      order, and a report with one entry per section detected as noise.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Pattern, Protocol, Sequence, Tuple, TypeVar

from app.core.config import settings
from app.schemas.ingestion import NOISE_CATEGORIES, NoiseReport, NoiseReportEntry

logger = logging.getLogger(__name__)

# Categories are checked in this order; the first one that matches wins.
_CATEGORY_ORDER = ("legal", "revision_history", "index_lists", "normative_appendix", "near_empty")

# Built-in patterns, used for any list the JSON file does not define.
# All patterns are compiled case-insensitively.
DEFAULT_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "legal": {
        "title_patterns": [
            r"copyright",
            r"derechos\s+de\s+autor",
            r"aviso\s+legal",
            r"informaci[oó]n\s+legal",
            r"legal\s+(?:notices?|information)",
            r"disclaimer",
            r"exenci[oó]n\s+de\s+responsabilidad",
            r"descargo\s+de\s+responsabilidad",
            r"marcas?\s+(?:registradas?|comerciales?)",
            r"trademarks?",
            r"t[eé]rminos\s+y\s+condiciones",
            r"terms\s+(?:and|of)\s+(?:conditions|use)",
            r"licencias?",
            r"licenses?",
            r"licensing",
            r"creative\s+commons",
            r"cr[eé]ditos?",
            r"credits?",
            r"colof[oó]n",
        ],
        "content_patterns": [
            r"©",
            r"\bcopyright\b",
            r"\ball\s+rights\s+reserved\b",
            r"\btodos\s+los\s+derechos\s+(?:est[aá]n\s+)?reservados\b",
            r"\bprohibid[ao]\s+(?:su|la|el)\s+(?:reproducci[oó]n|copia|distribuci[oó]n)\b",
            r"\bmarcas?\s+(?:registradas?|comerciales?)\b",
            r"\b(?:registered\s+)?trademarks?\b",
            r"\bdisclaimer\b",
            r"\bexenci[oó]n\s+de\s+responsabilidad\b",
            r"\bsin\s+previo\s+aviso\b",
            r"\bwithout\s+(?:prior\s+)?notice\b",
            r"\bcreative\s+commons\b",
            r"\bdistribuye\s+bajo\s+(?:una\s+)?licencia\b",
            r"\bdistributed\s+under\s+(?:a\s+)?(?:creative\s+commons|license)\b",
            r"\breconocimiento(?:‑|-|\s+)no\s*comercial\b",
            r"\bcopyleft\b",
            r"\blicencia\s+(?:de\s+uso|creative\s+commons|gpl|mit|apache|cc\b)",
        ],
    },
    "revision_history": {
        "title_patterns": [
            r"revision\s+history",
            r"version\s+history",
            r"revision\s+record",
            r"document\s+history",
            r"change\s*log",
            r"historial\s+de\s+(?:revisiones|cambios|versiones)",
            r"hist[oó]rico\s+de\s+(?:revisiones|cambios|versiones)",
            r"control\s+de\s+(?:cambios|versiones|revisiones)",
            r"registro\s+de\s+(?:cambios|revisiones)",
        ],
        # A line counts as a revision entry when it matches one of these
        # and also contains a year.
        "line_patterns": [
            r"^[\s|*\-]*(?:rev(?:isi[oó]n)?\.?|versi[oó]n|version)\s*[:\-]?\s*[A-Za-z0-9][\w.]*",
        ],
    },
    "index_lists": {
        # Matched against the whole title.
        "title_patterns": [
            r"^[íi]ndice(?:\s+(?:general|alfab[eé]tico|de\s+(?:contenidos?|tablas|figuras|ilustraciones|im[aá]genes|anexos|ap[eé]ndices)))?$",
            r"^tabla\s+de\s+contenidos?$",
            r"^contenidos?$",
            r"^table\s+of\s+contents$",
            r"^contents$",
            r"^list\s+of\s+(?:tables|figures|illustrations)$",
            r"^lista\s+de\s+(?:tablas|figuras|ilustraciones|im[aá]genes)$",
        ],
    },
    "near_empty": {
        # Matched against the whole title.
        "chapter_title_patterns": [
            r"^cap[ií]tulo\s+(?:\d+|[ivxlc]+)$",
            r"^chapter\s+(?:\d+|[ivxlc]+)$",
            r"^parte\s+(?:\d+|[ivxlc]+)$",
            r"^part\s+(?:\d+|[ivxlc]+)$",
            r"^secci[oó]n\s+\d+$",
            r"^section\s+\d+$",
        ],
        "blank_page_patterns": [
            r"p[áa]gina\s+(?:intencionalmente\s+)?(?:dejada\s+)?en\s+blanco",
            r"p[áa]gina\s+(?:se\s+)?dej[óo]\s+en\s+blanco",
            r"intencionalmente\s+(?:en\s+blanco|vac[ií]a)",
            r"intentionally\s+(?:left\s+)?blank",
            r"left\s+blank",
        ],
        # Safety notices are never discarded for being short.
        "protected_patterns": [
            r"\b(?:advertencia|peligro|precauci[oó]n|cuidado|atenci[oó]n|importante|warning|danger|caution|important)\b",
        ],
    },
    "normative_appendix": {
        "title_patterns": [
            r"declaraci[oó]n\s+(?:de\s+)?(?:conformidad|cumplimiento)",
            r"declaration\s+of\s+(?:conformity|compliance)",
            r"certificaciones",
            r"certifications",
            r"cumplimiento\s+(?:normativo|ambiental|regulatorio|reglamentario)",
            r"(?:regulatory|environmental)\s+(?:compliance|information)",
            r"informaci[oó]n\s+(?:regulatoria|normativa)",
            r"marcado\s+ce",
            r"ce\s+marking",
            # Case-sensitive so that "reach" (arm reach) is not mistaken for REACH.
            r"\b(?-i:RoHS|REACH|WEEE)\b",
        ],
    },
}

# A revision entry needs a year, so that a row such as "Versión del manual" is not counted.
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

# A table-of-contents line: dots (or an ellipsis) followed by a page number.
_DOT_LEADER_LINE = re.compile(r"(?:(?:\.[ \t]?){4,}|…+)[ \t]*(?:\d+|[ivxlcdm]+)[ \t]*$", re.IGNORECASE)
_MIN_DOT_LEADER_LINES = 2

_PREVIEW_CHARS = 80


class SectionLike(Protocol):
    """The attributes of a section the filter reads."""
    title: Optional[str]
    content: str
    page_number: Optional[int]


SectionT = TypeVar("SectionT", bound=SectionLike)


@dataclass
class NoiseThresholds:
    """Numeric limits that control the detection rules."""
    min_section_chars: int
    max_discard_ratio: float
    min_legal_patterns: int
    max_legal_section_chars: int
    min_revision_lines: int
    min_dot_leader_ratio: float
    protect_long_section_chars: int

    @classmethod
    def from_settings(cls) -> "NoiseThresholds":
        """Builds the thresholds from the NOISE_* values in settings."""
        return cls(
            min_section_chars=settings.NOISE_MIN_SECTION_CHARS,
            max_discard_ratio=settings.NOISE_MAX_DISCARD_RATIO,
            min_legal_patterns=settings.NOISE_MIN_LEGAL_PATTERNS,
            max_legal_section_chars=settings.NOISE_MAX_LEGAL_SECTION_CHARS,
            min_revision_lines=settings.NOISE_MIN_REVISION_LINES,
            min_dot_leader_ratio=settings.NOISE_MIN_DOT_LEADER_RATIO,
            protect_long_section_chars=settings.NOISE_PROTECT_LONG_SECTION_CHARS,
        )


def load_patterns(patterns_file: Optional[str] = None) -> Dict[str, Dict[str, List[Pattern]]]:
    """
    Returns the compiled patterns: the built-in defaults, with every list
    defined in the JSON file replacing its default. An unreadable file or an
    invalid pattern is logged and skipped, never raised, so a bad edit cannot
    stop ingestion.
    """
    raw: Dict[str, Dict[str, List[str]]] = {
        category: {key: list(values) for key, values in lists.items()}
        for category, lists in DEFAULT_PATTERNS.items()
    }

    path = Path(patterns_file) if patterns_file else None
    if path is not None and path.exists():
        try:
            overrides = json.loads(path.read_text(encoding="utf-8"))
            for category, lists in overrides.items():
                if category not in raw or not isinstance(lists, dict):
                    logger.warning("Ignoring unknown category '%s' in %s.", category, path.name)
                    continue
                for key, values in lists.items():
                    if key in raw[category] and isinstance(values, list):
                        raw[category][key] = [str(value) for value in values]
                    else:
                        logger.warning("Ignoring unknown list '%s.%s' in %s.", category, key, path.name)
        except (OSError, ValueError) as exc:
            logger.warning("Could not read noise patterns file %s (%s). Using defaults.", path, exc)
    elif path is not None:
        logger.info("Noise patterns file %s not found. Using built-in defaults.", path)

    compiled: Dict[str, Dict[str, List[Pattern]]] = {}
    for category, lists in raw.items():
        compiled[category] = {}
        for key, values in lists.items():
            compiled[category][key] = []
            for value in values:
                try:
                    compiled[category][key].append(re.compile(value, re.IGNORECASE))
                except re.error as exc:
                    logger.warning("Skipping invalid pattern '%s' in %s.%s: %s", value, category, key, exc)
    return compiled


class NoiseFilter:
    """Detects noise sections and removes them from a document's section list."""

    def __init__(
        self,
        patterns_file: Optional[str] = None,
        thresholds: Optional[NoiseThresholds] = None,
    ):
        self._patterns = load_patterns(patterns_file if patterns_file is not None else settings.NOISE_PATTERNS_FILE)
        self._limits = thresholds or NoiseThresholds.from_settings()

        # Maps each category to the method that detects it.
        self._detectors: Dict[str, Callable[[str, str], Optional[str]]] = {
            "legal": self._detect_legal,
            "revision_history": self._detect_revision_history,
            "index_lists": self._detect_index_lists,
            "normative_appendix": self._detect_normative_appendix,
            "near_empty": self._detect_near_empty,
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def filter_sections(
        self,
        sections: Sequence[SectionT],
        categories: Optional[Sequence[str]] = None,
        dry_run: bool = False,
    ) -> Tuple[List[SectionT], NoiseReport]:
        """
        Returns the sections to keep and a report. Sections are discarded only
        when the filter is not in dry-run mode and no safeguard applies;
        otherwise every section is returned and the report explains why.
        The report's character counts always describe what was detected.
        """
        active = set(categories) if categories else set(NOISE_CATEGORIES)

        detections: Dict[int, Tuple[str, str]] = {}
        for position, section in enumerate(sections):
            detection = self._classify(section, active)
            if detection is not None:
                detections[position] = detection

        total_chars = sum(len(section.content or "") for section in sections)
        noise_chars = sum(len(sections[position].content) for position in detections)
        ratio = noise_chars / total_chars if total_chars else 0.0

        report = NoiseReport(
            dry_run=dry_run,
            total_chars=total_chars,
            discarded_chars=noise_chars,
            discard_ratio=round(ratio, 4),
        )
        if not detections:
            return list(sections), report

        skip_reason = self._skip_reason(len(detections), len(sections), ratio)
        apply_filter = not dry_run and skip_reason is None

        for position, (category, reason) in detections.items():
            section = sections[position]
            report.entries.append(
                NoiseReportEntry(
                    category=category,
                    reason=reason,
                    section_title=section.title,
                    page_number=section.page_number,
                    char_count=len(section.content),
                    preview=self._preview(section.content),
                    discarded=apply_filter,
                )
            )

        if skip_reason is not None and not dry_run:
            report.skipped_reason = skip_reason
            logger.warning("Noise filter skipped: %s.", skip_reason)

        if not apply_filter:
            return list(sections), report

        for entry in report.entries:
            logger.info(
                "Noise filter discarded section %r (%s: %s, %d chars).",
                entry.section_title, entry.category, entry.reason, entry.char_count,
            )
        kept = [section for position, section in enumerate(sections) if position not in detections]
        return kept, report

    # ── Classification ─────────────────────────────────────────────────────────

    def _classify(self, section: SectionLike, active: set) -> Optional[Tuple[str, str]]:
        """Returns (category, reason) for the first matching active category, or None.
        Sections with no content produce no chunks, so they are never evaluated."""
        content = section.content or ""
        if not content.strip():
            return None

        title = self._normalize_title(section.title)
        for category in _CATEGORY_ORDER:
            if category not in active:
                continue
            reason = self._detectors[category](title, content)
            if reason is not None:
                return category, reason
        return None

    def _skip_reason(self, detected: int, total: int, ratio: float) -> Optional[str]:
        """Returns why the filter must not be applied, or None when it is safe."""
        if detected == total:
            return "every section was detected as noise"
        if ratio > self._limits.max_discard_ratio:
            return (
                f"detected noise is {ratio:.0%} of the text, "
                f"above the {self._limits.max_discard_ratio:.0%} limit"
            )
        return None

    # ── Detectors (each returns a reason string, or None) ──────────────────────

    def _detect_legal(self, title: str, content: str) -> Optional[str]:
        """Legal pages: a legal title, or a short section dense in legal phrases."""
        patterns = self._patterns["legal"]

        matched = self._first_match(patterns["title_patterns"], title)
        if matched is not None:
            return f"title matches /{matched.pattern}/"

        if len(content) <= self._limits.max_legal_section_chars:
            hits = [pattern for pattern in patterns["content_patterns"] if pattern.search(content)]
            if len(hits) >= self._limits.min_legal_patterns:
                return f"content matches {len(hits)} distinct legal patterns"
        return None

    def _detect_revision_history(self, title: str, content: str) -> Optional[str]:
        """Revision tables: a revision title, or several dated revision lines in a non-long section."""
        patterns = self._patterns["revision_history"]

        matched = self._first_match(patterns["title_patterns"], title)
        if matched is not None:
            return f"title matches /{matched.pattern}/"

        if len(content) <= self._limits.protect_long_section_chars:
            revision_lines = sum(
                1 for line in content.split("\n")
                if _YEAR.search(line) and any(pattern.search(line) for pattern in patterns["line_patterns"])
            )
            if revision_lines >= self._limits.min_revision_lines:
                return f"{revision_lines} dated revision lines"
        return None

    def _detect_index_lists(self, title: str, content: str) -> Optional[str]:
        """Indexes: an index title, or a large share of lines ending in dot leaders and a page number."""
        matched = self._first_match(self._patterns["index_lists"]["title_patterns"], title)
        if matched is not None:
            return f"title matches /{matched.pattern}/"

        lines = [line for line in content.split("\n") if line.strip()]
        leader_lines = sum(1 for line in lines if _DOT_LEADER_LINE.search(line.strip()))
        if leader_lines >= _MIN_DOT_LEADER_LINES and leader_lines / len(lines) >= self._limits.min_dot_leader_ratio:
            return f"{leader_lines} of {len(lines)} lines are dot leaders with page numbers"
        return None

    def _detect_normative_appendix(self, title: str, content: str) -> Optional[str]:
        """Normative appendices are detected by title only, never by content."""
        matched = self._first_match(self._patterns["normative_appendix"]["title_patterns"], title)
        if matched is not None:
            return f"title matches /{matched.pattern}/"
        return None

    def _detect_near_empty(self, title: str, content: str) -> Optional[str]:
        """
        Chapter dividers and blank pages: little useful text, and either no
        title, a chapter-style title, or a "blank page" phrase. A short section
        with a real title (for example a one-line note) is kept, and so is any
        section that looks like a safety notice.
        """
        patterns = self._patterns["near_empty"]

        if any(pattern.search(title) or pattern.search(content) for pattern in patterns["protected_patterns"]):
            return None

        # Useful text is the alphanumeric characters left once blank-page phrases are removed.
        remaining = content
        blank_page = False
        for pattern in patterns["blank_page_patterns"]:
            if pattern.search(remaining):
                blank_page = True
                remaining = pattern.sub(" ", remaining)
        useful_chars = sum(1 for char in remaining if char.isalnum())

        if useful_chars >= self._limits.min_section_chars:
            return None
        if not title:
            return f"no title and only {useful_chars} useful characters"
        if self._first_match(patterns["chapter_title_patterns"], title) is not None:
            return f"chapter divider with only {useful_chars} useful characters"
        if blank_page:
            return "blank page"
        return None

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _first_match(patterns: List[Pattern], text: str) -> Optional[Pattern]:
        """Returns the first pattern found in the text, or None (also for empty text)."""
        if not text:
            return None
        for pattern in patterns:
            if pattern.search(text):
                return pattern
        return None

    @staticmethod
    def _normalize_title(title: Optional[str]) -> str:
        """Collapses whitespace and trims surrounding punctuation from a title; None becomes ''."""
        if not title:
            return ""
        return re.sub(r"\s+", " ", title).strip().strip(":.-–— ")

    @staticmethod
    def _preview(content: str) -> str:
        """Returns the start of the content as a single line."""
        return re.sub(r"\s+", " ", content).strip()[:_PREVIEW_CHARS]