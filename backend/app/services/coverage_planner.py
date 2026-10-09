"""
coverage_planner.py

Purpose:
    Analyzes the full set of parent chunks for a document and produces a
    CoveragePlan that distributes generation targets across document sections.
    Prevents all generation from concentrating on the first few retrieved
    chunks and estimates whether the document has enough substantive content
    to satisfy the requested item count.

Input:
    - parent_chunks: all parent chunks produced by IngesterService for a document.
    - output_format: one of flashcards, quiz, tutorial, resumen ejecutivo, guion de clase.
    - requested_items: the target item count before capacity adjustment.
    - language: output language string (used for warning messages).

Output:
    - CoveragePlan with a list of SectionPlan entries, a viable item cap, and
      an optional capacity warning.
"""

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Noise section titles to skip during section inventory
# ---------------------------------------------------------------------------
_NOISE_TITLES: frozenset = frozenset({
    # Spanish
    "indice", "tabla de contenido", "tabla de contenidos", "introduccion",
    "referencias", "bibliografia", "anexo", "apendice", "glosario",
    "conclusion", "conclusiones", "portada", "resumen", "agradecimientos",
    "dedicatoria", "prologo", "prefacio", "lista de figuras", "lista de tablas",
    "licencia", "licencias", "creditos", "colofon", "aviso legal",
    # English
    "table of contents", "contents", "introduction", "references", "bibliography",
    "appendix", "annex", "glossary", "conclusion", "conclusions", "summary",
    "overview", "acknowledgements", "dedication", "foreword", "preface",
    "list of figures", "list of tables", "license", "licenses", "licensing",
    "credits", "legal notice", "disclaimer",
    # Portuguese
    "sumario", "indice geral", "referencias bibliograficas",
})

_NOISE_SUBSTRINGS: tuple = (
    "table of content", "tabla de contenido", "list of figure",
    "list of table", "lista de figur", "lista de tabla",
    "creative common", "creative commons", "licencia", "license",
)

# Minimum character count for a chunk to be considered substantive
_MIN_SUBSTANTIVE_CHARS = 80

# Items-per-1000-chars capacity factors, conservative estimates per format
_CAPACITY_CHARS_PER_ITEM: Dict[str, int] = {
    "flashcards": 300,
    "flashcard": 300,
    "quiz": 500,
    "tutorial": 700,
    "resumen ejecutivo": 900,
    "resumen": 900,
    "executive_summary": 900,
    "guion de clase": 800,
    "guion": 800,
    "class_script": 800,
}

# Formats where output should be one holistic generation from aggregated context
_HOLISTIC_FORMATS: frozenset = frozenset({
    "resumen ejecutivo", "resumen", "executive_summary",
})

# Formats where output follows document order (tutorial, video script)
_SEQUENTIAL_FORMATS: frozenset = frozenset({
    "tutorial",
    "guion de clase", "guion", "class_script",
})


@dataclass
class SectionPlan:
    """Generation plan for one document section."""

    section_title: str
    # Ordered parent chunks belonging to this section
    parent_chunks: List[Dict[str, Any]]
    # Number of items to generate from this section
    allocated_items: int
    # Concatenated context sent to the LLM prompt (first N chars)
    context_snippet: str
    # Chunk IDs for grounding verification
    chunk_ids: List[str]
    # Representative chunk_id for source provenance
    primary_chunk_id: str
    # Page number (if available from paged source)
    page_number: Optional[int] = None


@dataclass
class CoveragePlan:
    """Document-wide generation plan."""

    sections: List[SectionPlan]
    # Maximum items the document can support without fabrication
    total_capacity: int
    # min(requested_items, total_capacity)
    viable_target: int
    # Non-None when viable_target < requested_items
    capacity_warning: Optional[str]
    # "distributed" | "sequential" | "holistic"
    strategy: str
    # Total substantive content chars used for capacity estimation
    total_content_chars: int = 0


# ---------------------------------------------------------------------------
# CoveragePlanner
# ---------------------------------------------------------------------------

class CoveragePlanner:
    """
    Builds a document-aware generation plan from the full parent chunk list.

    Usage:
        plan = CoveragePlanner().plan(
            parent_chunks=doc_data["parent_chunks"],
            output_format="flashcards",
            requested_items=20,
        )
    """

    def plan(
        self,
        parent_chunks: List[Dict[str, Any]],
        output_format: str,
        requested_items: int,
        language: str = "Spanish",
        context_snippet_chars: int = 600,
    ) -> CoveragePlan:
        """
        Analyzes parent_chunks and returns a CoveragePlan for the requested format.
        """
        fmt = (output_format or "flashcards").lower().strip()

        substantive = self._filter_substantive(parent_chunks)
        if not substantive:
            # Fall back to all chunks if everything looks like noise
            substantive = parent_chunks

        sections = self._group_by_section(substantive)
        total_chars = sum(
            len(ch.get("content", "")) for ch in substantive
        )

        chars_per_item = _CAPACITY_CHARS_PER_ITEM.get(fmt, 500)
        total_capacity = max(1, total_chars // chars_per_item)

        viable_target = min(requested_items, total_capacity)
        warning = None
        if viable_target < requested_items:
            warning = self._capacity_warning(viable_target, requested_items, language)
            logger.info(
                "CoveragePlanner: capping %d → %d items (content: %d chars, format: %s)",
                requested_items, viable_target, total_chars, fmt,
            )

        if fmt in _HOLISTIC_FORMATS:
            strategy = "holistic"
            section_plans = self._build_holistic_plan(
                sections, viable_target, context_snippet_chars
            )
        elif fmt in _SEQUENTIAL_FORMATS:
            strategy = "sequential"
            section_plans = self._build_sequential_plan(
                sections, viable_target, context_snippet_chars
            )
        else:
            strategy = "distributed"
            section_plans = self._build_distributed_plan(
                sections, viable_target, context_snippet_chars
            )

        logger.info(
            "CoveragePlanner: strategy=%s sections=%d viable=%d/%d",
            strategy, len(section_plans), viable_target, requested_items,
        )

        return CoveragePlan(
            sections=section_plans,
            total_capacity=total_capacity,
            viable_target=viable_target,
            capacity_warning=warning,
            strategy=strategy,
            total_content_chars=total_chars,
        )

    # ---------------------------------------------------------------------------
    # Section inventory helpers
    # ---------------------------------------------------------------------------

    def _filter_substantive(
        self, parent_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Drops chunks that are too short or whose title is pure metadata noise."""
        result = []
        for chunk in parent_chunks:
            raw_title = (chunk.get("title") or "").strip().lower()
            content = chunk.get("content") or ""

            # Normalize title by stripping leading section numbers or markers (e.g., "5 Licencia", "5. Licencia")
            clean_title = re.sub(r"^[\d\.\-\)\s]+", "", raw_title).strip()

            # Skip noise section titles
            if raw_title in _NOISE_TITLES or clean_title in _NOISE_TITLES:
                continue
            if any(sub in raw_title for sub in _NOISE_SUBSTRINGS) or any(sub in clean_title for sub in _NOISE_SUBSTRINGS):
                continue

            # Skip chunks whose content is shorter than the minimum threshold
            if len(content.strip()) < _MIN_SUBSTANTIVE_CHARS:
                continue

            result.append(chunk)
        return result

    def _group_by_section(
        self, chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups chunks by normalized section title. Preserves document order
        through insertion-ordered dict. Chunks without a title are grouped
        under a synthetic title derived from their position.
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}
        unnamed_counter = 0
        for chunk in chunks:
            raw_title = chunk.get("title") or ""
            # Strip breadcrumb suffix (e.g. "Doc > Section" → use full string as key)
            title_key = raw_title.strip() if raw_title.strip() else None
            if not title_key:
                unnamed_counter += 1
                title_key = f"Sección {unnamed_counter}"
            if title_key not in groups:
                groups[title_key] = []
            groups[title_key].append(chunk)
        return groups

    # ---------------------------------------------------------------------------
    # Plan builders
    # ---------------------------------------------------------------------------

    def _build_distributed_plan(
        self,
        sections: Dict[str, List[Dict[str, Any]]],
        viable_target: int,
        context_snippet_chars: int,
    ) -> List[SectionPlan]:
        """
        Distributes viable_target items proportionally across sections based on
        content volume. Every section gets at least 1 item.
        """
        section_items = list(sections.items())
        n = len(section_items)
        if n == 0:
            return []

        # Compute weights by character count
        weights = [
            sum(len(ch.get("content", "")) for ch in chunks)
            for _, chunks in section_items
        ]
        total_weight = sum(weights) or 1

        # Proportional allocation with floor = 1
        allocated = [max(1, math.floor(viable_target * w / total_weight)) for w in weights]

        # Adjust rounding differences
        diff = viable_target - sum(allocated)
        if diff > 0:
            # Add remainder to the heaviest sections first
            order = sorted(range(n), key=lambda i: weights[i], reverse=True)
            for i in order[:diff]:
                allocated[i] += 1
        elif diff < 0:
            # Remove from the smallest sections first (keep min=1)
            order = sorted(range(n), key=lambda i: allocated[i], reverse=True)
            for i in order[:-diff]:
                if allocated[i] > 1:
                    allocated[i] -= 1

        plans = []
        for (title, chunks), items in zip(section_items, allocated):
            if items <= 0:
                continue
            plans.append(self._make_section_plan(title, chunks, items, context_snippet_chars))
        return plans

    def _build_sequential_plan(
        self,
        sections: Dict[str, List[Dict[str, Any]]],
        viable_target: int,
        context_snippet_chars: int,
    ) -> List[SectionPlan]:
        """
        Keeps document section order and distributes items evenly, suitable
        for tutorials and video scripts where sequence matters pedagogically.
        """
        return self._build_distributed_plan(sections, viable_target, context_snippet_chars)

    def _build_holistic_plan(
        self,
        sections: Dict[str, List[Dict[str, Any]]],
        viable_target: int,
        context_snippet_chars: int,
    ) -> List[SectionPlan]:
        """
        Aggregates all sections into a single synthetic section for formats
        that require a global view (executive summary). The LLM receives a
        representative sample from the entire document rather than one chunk.
        """
        all_chunks: List[Dict[str, Any]] = []
        for chunks in sections.values():
            all_chunks.extend(chunks)

        if not all_chunks:
            return []

        # Build a global context by sampling from every section
        sampled_parts = []
        chars_used = 0
        max_total = context_snippet_chars * 4  # allow more context for holistic
        section_names = list(sections.keys())
        for sec_name, chunks in sections.items():
            for chunk in chunks:
                fragment = chunk.get("content", "")[:300].strip()
                if fragment:
                    sampled_parts.append(f"[{sec_name}] {fragment}")
                    chars_used += len(fragment)
                    if chars_used >= max_total:
                        break
            if chars_used >= max_total:
                break

        global_context = "\n\n".join(sampled_parts)
        chunk_ids = [c.get("id", "") for c in all_chunks if c.get("id")]
        primary_id = chunk_ids[0] if chunk_ids else "chunk-001"

        # Infer primary page from first chunk with a valid page number
        page = None
        for chunk in all_chunks:
            p = chunk.get("metadata", {}).get("page_number")
            if isinstance(p, int) and p > 0:
                page = p
                break

        return [
            SectionPlan(
                section_title=section_names[0] if section_names else "Documento completo",
                parent_chunks=all_chunks,
                allocated_items=viable_target,
                context_snippet=global_context[:context_snippet_chars * 4],
                chunk_ids=chunk_ids,
                primary_chunk_id=primary_id,
                page_number=page,
            )
        ]

    # ---------------------------------------------------------------------------
    # SectionPlan factory
    # ---------------------------------------------------------------------------

    def _make_section_plan(
        self,
        title: str,
        chunks: List[Dict[str, Any]],
        allocated_items: int,
        context_snippet_chars: int,
    ) -> SectionPlan:
        """Assembles a SectionPlan from a group of chunks for one section."""
        combined_content = "\n\n".join(
            chunk.get("content", "") for chunk in chunks
        )
        context_snippet = combined_content[:context_snippet_chars]
        chunk_ids = [c.get("id", "") for c in chunks if c.get("id")]
        primary_id = chunk_ids[0] if chunk_ids else "chunk-001"

        # Page number from the first chunk in the section that has one
        page = None
        for chunk in chunks:
            p = chunk.get("metadata", {}).get("page_number")
            if isinstance(p, int) and p > 0:
                page = p
                break

        return SectionPlan(
            section_title=title,
            parent_chunks=chunks,
            allocated_items=allocated_items,
            context_snippet=context_snippet,
            chunk_ids=chunk_ids,
            primary_chunk_id=primary_id,
            page_number=page,
        )

    # ---------------------------------------------------------------------------
    # Capacity warning messages
    # ---------------------------------------------------------------------------

    @staticmethod
    def _capacity_warning(viable: int, requested: int, language: str) -> str:
        is_spanish = "es" in language.lower()
        if is_spanish:
            return (
                f"El documento tiene contenido suficiente para generar {viable} elemento(s) "
                f"con calidad verificada. Se solicitaron {requested}. "
                "Se generará la cantidad viable sin incluir contenido inventado."
            )
        return (
            f"The document has enough content to generate {viable} verified item(s). "
            f"{requested} were requested. "
            "Only the viable count will be generated; no fabricated content will be added."
        )
