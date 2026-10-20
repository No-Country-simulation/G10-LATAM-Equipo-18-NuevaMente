"""
pipeline_stages.py

Purpose:
    Reusable stages and helpers for the educational content adaptation pipeline:
    coverage planning, batch generation with LLM cascades, deduplication, source
    citation verification, quality auditing, capacity capping and response
    assembly. LangGraphOrchestrator composes these stages as graph nodes; this
    module owns the shared logic and the per-run model tracking.

Input:
    - request (AdaptationRequest): user customization preferences and constraints.
    - top_passages (List[Dict[str, Any]]): RAG-retrieved document parent/child context.
    - all_parent_chunks (List[Dict[str, Any]]): full set of parent chunks for coverage planning.
    - key_concepts (List[str]): extracted key domain concepts.
    - prerequisites (List[str]): detected concept dependencies.
    - tracer (Optional[PipelineTracer]): execution telemetry and stage timing.

Output:
    - AdaptationResponse: structured educational material with metadata and artifact storage reference.
"""

import difflib
import hashlib
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple
from app.services.rate_guard import get_llm_guard

from app.core.config import settings
from app.core.labels import (
    TITLE_TEMPLATES_ES,
    get_capacity_warning,
    get_contextualized_intro,
)
from app.infrastructure.llm import GeminiClient, GroqClient, OpenRouterClient
from app.prompts.prompt_loader import load_prompt
from app.schemas.adaptation import (
    AdaptationRequest,
    AdaptationResponse,
    AdaptedContent,
    QualityEvaluation,
    QuizItem,
    RagFuente,
)
from app.services.coverage_planner import CoveragePlan, SectionPlan
from app.services.multi_agent_router import MultiAgentRouter

logger = logging.getLogger("PipelineStages")


def _is_spanish(target_language: Optional[str]) -> bool:
    """Returns True if the target language is Spanish (default), False otherwise."""
    if not target_language:
        return True
    lang = target_language.strip().lower()
    return lang.startswith("es") or "span" in lang


def _clean_concept_text(raw_concept: str, context: str = "", doc_title: str = "") -> str:
    """Sanitizes raw concept strings stripping markdown, page numbering, roman numeral
    noise, and trailing binary/punctuation artifacts.
    Falls back to meaningful terms extracted from context or doc_title when the result
    is non-substantive.
    """
    if not raw_concept:
        raw_concept = ""
    # Strip markdown headers, bold, italics, backticks, blockquotes
    clean = re.sub(r"[\#\*\_\~\`\>]+", "", str(raw_concept)).strip()
    # Strip PDF xref/EOF artifacts
    clean = re.sub(r"(?:%?\s*startxref[\s\d]*|%%EOF|xref\s*\d+\s*\d+|\b\d{5,}\b)", "", clean, flags=re.IGNORECASE).strip()
    # Strip embedded page number patterns: "53 de 363", "página 12"
    clean = re.sub(r"\b\d+\s*(?:de|of|/)\s*\d+\b", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"\b(?:p[áa]gina|page)\s*\d+\b", "", clean, flags=re.IGNORECASE).strip()
    # Strip leading numbering or punctuation (e.g. "1.2. ", "VII.", ":", "-")
    clean = re.sub(r"^[\d\.\-\)\:\,\;\s]+", "", clean).strip()
    clean = re.sub(r"[\:\%\-_\.\,\;\s]+$", "", clean).strip()
    # Strip dangling connectors left after page-number removal
    dangling_pat = re.compile(r"\b(?:de|en|sobre|para|con|of|for|the|el|la|los|las|y)\s*$", re.IGNORECASE)
    for _ in range(3):
        new_clean = dangling_pat.sub("", clean).strip()
        new_clean = re.sub(r"[\:\%\-_\.\,\;\s]+$", "", new_clean).strip()
        if new_clean == clean:
            break
        clean = new_clean

    is_roman = bool(re.match(r"^[IVXLCDMivxlcdm\s\.]+$", clean))
    is_number = bool(re.match(r"^\d+$", clean))
    is_truncated_prefix = clean.lower() in {
        "configuración y aplicación", "configuración y aplicación de",
        "configuración", "aplicación", "implementación", "implementar",
        "configuring and applying", "configuration and application", "configuration",
    }

    # When cleaned result is invalid, extract from context or doc_title
    if is_roman or is_number or is_truncated_prefix or len(clean) < 3 or re.match(r"^[\W_]+$", clean):
        fallback_term = ""
        if context:
            words = [
                w for w in re.findall(r"[A-ZÁÉÍÓÚÜÑa-záéíóúüñ]{4,}", context)
                if w.lower() not in {
                    "este", "esta", "para", "como", "sobre", "desde", "hasta",
                    "pagina", "page", "section", "seccion", "capitulo", "chapter",
                    "configuracion", "configuración", "aplicacion", "aplicación",
                    "implementar", "implementación", "siguiendo", "directrices", "tecnicas", "técnicas"
                }
            ]
            if len(words) >= 2:
                fallback_term = " ".join(words[:3]).capitalize()
            elif words:
                fallback_term = words[0].capitalize()
        if not fallback_term or len(fallback_term) < 3:
            fallback_term = doc_title.strip() if doc_title and len(doc_title.strip()) > 2 else "Componente Técnico"
        if is_truncated_prefix:
            clean = f"{clean} de {fallback_term}"
        else:
            clean = fallback_term

    return clean


QUANTITY_TABLE: Dict[str, Dict[str, int]] = {
    settings.FORMAT_FLASHCARDS: {"breve": 10, "estandar": 20, "amplio": 40, "exhaustivo": 80, "brief": 10, "standard": 20, "wide": 40, "comprehensive": 80},
    settings.FORMAT_QUIZ: {"breve": 5, "estandar": 10, "amplio": 20, "exhaustivo": 30, "brief": 5, "standard": 10, "wide": 20, "comprehensive": 30},
    settings.FORMAT_TUTORIAL: {"breve": 4, "estandar": 8, "amplio": 15, "exhaustivo": 25, "brief": 4, "standard": 8, "wide": 15, "comprehensive": 25},
    settings.FORMAT_SUMMARY: {"breve": 3, "estandar": 5, "amplio": 10, "exhaustivo": 15, "brief": 3, "standard": 5, "wide": 10, "comprehensive": 15},
    settings.FORMAT_CLASS_SCRIPT: {"breve": 3, "estandar": 5, "amplio": 8, "exhaustivo": 12, "brief": 3, "standard": 5, "wide": 8, "comprehensive": 12},
    # Spanish aliases
    "resumen ejecutivo": {"breve": 3, "estandar": 5, "amplio": 10, "exhaustivo": 15, "brief": 3, "standard": 5, "wide": 10, "comprehensive": 15},
    "guion de clase": {"breve": 3, "estandar": 5, "amplio": 8, "exhaustivo": 12, "brief": 3, "standard": 5, "wide": 8, "comprehensive": 12},
}

FORMAT_CAPACITY_FACTOR: Dict[str, int] = {
    settings.FORMAT_FLASHCARDS: 8,
    settings.FORMAT_QUIZ: 4,
    settings.FORMAT_TUTORIAL: 3,
    settings.FORMAT_SUMMARY: 2,
    settings.FORMAT_CLASS_SCRIPT: 2,
    # Spanish aliases
    "resumen ejecutivo": 2,
    "guion de clase": 2,
}


class PipelineStages:
    """Reusable stages and helpers composing the adaptation pipeline."""

    def __init__(self):
        self.gemini_client = GeminiClient()
        self.groq_client = GroqClient()
        self.openrouter_client = OpenRouterClient()
        # Map of active providers
        self._provider_map = {
            "gemini": self.gemini_client,
            "groq": self.groq_client,
            "openrouter": self.openrouter_client,
        }
        # Tracks the name of the LLM provider that last succeeded in the cascade
        self.last_provider: str = "fallback"
        self.last_model: Optional[str] = None
        self.critic_provider: str = "fallback"
        self.critic_model: Optional[str] = None
        self._models_used: Dict[str, set] = {}
        self.router = MultiAgentRouter()
        self._response_cache: Dict[str, AdaptationResponse] = {}

    # ---------------------------------------------------------------------------
    # STAGE A: PLANNER
    # ---------------------------------------------------------------------------
    def _stage_planner(
        self,
        doc_title: str,
        key_concepts: List[str],
        coverage_plan: CoveragePlan,
        target: int,
        target_language: str = "Spanish",
    ) -> List[Dict[str, Any]]:
        """
        Converts CoveragePlan sections into ordered topic descriptors.
        Each SectionPlan becomes one or more topic entries with the section's
        allocated item count and context snippet.
        """
        is_spanish = "es" in (target_language or "spanish").lower()
        topics: List[Dict[str, Any]] = []

        for sp in coverage_plan.sections:
            if sp.allocated_items <= 0:
                continue

            # Use key_concepts to enrich topic label when available
            concept = self._best_concept_for_section(sp.section_title, key_concepts)

            # Clean raw section titles of leading numbers (e.g. "1.2 Componentes" -> "Componentes")
            clean_section = re.sub(r"^[\d\.\-\)\s]+", "", sp.section_title).strip()
            topic_label = (
                f"{concept}" if concept != sp.section_title and concept != clean_section
                else (clean_section if clean_section else sp.section_title)
            )

            topics.append({
                "topic": topic_label,
                "concept": concept,
                "target_items": sp.allocated_items,
                "chunk_id": sp.primary_chunk_id,
                "page": sp.page_number,
                "section": sp.section_title,
                "breadcrumb": sp.parent_chunks[0].get("breadcrumb") if sp.parent_chunks else "",
                "context": sp.context_snippet[:settings.RAG_CONTEXT_SNIPPET_SIZE],
            })

        if not topics:
            # Fallback: single topic from document title
            topics.append({
                "topic": doc_title,
                "concept": doc_title,
                "target_items": target,
                "chunk_id": "chunk-001",
                "page": None,
                "section": doc_title,
                "breadcrumb": "",
                "context": doc_title,
            })

        return topics

    @staticmethod
    def _best_concept_for_section(section_title: str, key_concepts: List[str]) -> str:
        """Returns the key concept most lexically similar to the section title,
        or the section title itself if no key concepts are available."""
        if not key_concepts:
            return section_title
        title_lower = section_title.lower()
        for concept in key_concepts:
            if concept.lower() in title_lower or title_lower in concept.lower():
                return concept
        return section_title

    def _stage_batch_generators(
        self,
        request: AdaptationRequest,
        doc_title: str,
        topics: List[Dict[str, Any]],
        passages: List[Dict[str, Any]],
        target: int,
        target_language: str,
        tracer: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        batch_size = 5 if target <= 10 else (8 if target <= 30 else 10)

        # Map output format to a specific prompt template file.
        fmt_key = (request.output_format or "flashcards").lower()
        format_prompt_map = {
            "flashcards": "formats/flashcards.md",
            "quiz": "formats/quiz.md",
            "tutorial": "formats/tutorial.md",
            "resumen ejecutivo": "formats/executive_summary.md",
            "guion de clase": "formats/video_script.md",
        }
        prompt_file = format_prompt_map.get(fmt_key, "writer.md")
        template = load_prompt(prompt_file)

        # Pre-format writer system instruction once for the entire batch stage
        writer_system_tmpl = load_prompt("writer_system.md")
        system_instruction = writer_system_tmpl.format(
            niche=request.niche,
            recipient_profile=request.recipient_profile,
            target_language=target_language,
            detail_level=request.detail_level,
        )

        cascade = self.router.get_model_cascade(fmt_key)
        if not cascade:
            cascade = [{"provider": k, "model": None} for k in self.router.get_cascade_order(fmt_key)]
        guard = get_llm_guard()

        # Optimization: for compact requests (target <= 10) with multiple topics,
        # consolidate all topics into a single LLM prompt call instead of multiple sequential round-trips.
        # Executive summary always consolidates regardless of target count to ensure a holistic output.
        is_summary_format = "resumen" in fmt_key or "executive_summary" in fmt_key
        if (target <= 10 or is_summary_format) and len(topics) > 1:
            consolidated_chunks = []
            topic_names = []
            for t in topics:
                s_lbl = t.get("section") or "Unknown section"
                b_lbl = t.get("breadcrumb") or ""
                p_val = t.get("page")
                p_lbl = f" | p.{p_val}" if p_val is not None else ""
                consolidated_chunks.append(
                    f"[{t['chunk_id']}] SECTION: {s_lbl}"
                    f"{(' | ' + b_lbl) if b_lbl else ''}"
                    f"{p_lbl}\n{t['context']}"
                )
                if t.get("topic"):
                    topic_names.append(t["topic"])

            combined_chunk_info = "\n\n---\n\n".join(consolidated_chunks)
            combined_topic = ", ".join(dict.fromkeys(topic_names))
            first_topic = topics[0]
            first_page_val = first_topic.get("page")

            prompt = template.format(
                niche=request.niche,
                recipient_profile=request.recipient_profile,
                detail_level=request.detail_level,
                output_format=request.output_format,
                topic=combined_topic,
                item_count=target,
                target_language=target_language,
                chunk_info=combined_chunk_info,
                chunk_id=first_topic["chunk_id"],
                page_number=first_page_val if first_page_val is not None else "N/A",
            )

            raw = None
            if tracer:
                tracer.record_llm_call("generar")

            for entry in cascade:
                llm = self._provider_map.get(entry["provider"])
                if not llm or not llm.is_available or not guard.should_attempt(entry["provider"], entry.get("model")):
                    continue
                guard.wait_for_slot(entry["provider"], entry.get("model"))
                try:
                    raw = llm.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        json_output=True,
                        model_name=entry.get("model"),
                    )
                    if raw:
                        self.last_provider = entry["provider"]
                        self.last_model = entry.get("model")
                        self._track_model(entry["provider"], entry.get("model"))
                        guard.record_success(entry["provider"], entry.get("model"))
                        logger.info("Lote consolidado (%d ítems) generado con %s/%s", target, entry["provider"], entry.get("model"))
                        break
                except Exception as exc:
                    guard.record_failure(entry["provider"], entry.get("model"))
                    logger.warning("%s/%s generation failed: %s", entry["provider"], entry.get("model"), exc)

            parsed_batch = self._parse_json_batch(raw)
            if parsed_batch:
                items.extend(parsed_batch[:target])
                return items
            logger.info("Consolidated batch parsing failed or returned empty; falling back to per-topic generation.")

        for topic_idx, topic in enumerate(topics):
            if len(items) >= target:
                break

            # Respect section-level allocation from the coverage plan when present
            section_cap = topic.get("target_items", batch_size)
            n_items = min(section_cap, batch_size, target - len(items))

            # Build structural reference line; include page only when available.
            section_label = topic.get("section") or "Unknown section"
            breadcrumb_label = topic.get("breadcrumb") or ""
            page_val = topic.get("page")
            page_label = f" | p.{page_val}" if page_val is not None else ""
            chunk_info = (
                f"[{topic['chunk_id']}] SECTION: {section_label}"
                f"{(' | ' + breadcrumb_label) if breadcrumb_label else ''}"
                f"{page_label}\n{topic['context']}"
            )

            prompt = template.format(
                niche=request.niche,
                recipient_profile=request.recipient_profile,
                detail_level=request.detail_level,
                output_format=request.output_format,
                topic=topic["topic"],
                item_count=n_items,
                target_language=target_language,
                chunk_info=chunk_info,
                chunk_id=topic["chunk_id"],
                page_number=page_val if page_val is not None else "N/A",
            )

            raw = None
            if tracer:
                tracer.record_llm_call("generar")

            for entry in cascade:
                llm = self._provider_map.get(entry["provider"])
                if not llm or not llm.is_available or not guard.should_attempt(entry["provider"], entry.get("model")):
                    continue
                guard.wait_for_slot(entry["provider"], entry.get("model"))
                try:
                    raw = llm.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        json_output=True,
                        model_name=entry.get("model"),
                    )
                    if raw:
                        self.last_provider = entry["provider"]
                        self.last_model = entry.get("model")
                        self._track_model(entry["provider"], entry.get("model"))
                        guard.record_success(entry["provider"], entry.get("model"))
                        logger.info("Lote generado con %s/%s", entry["provider"], entry.get("model"))
                        break
                except Exception as exc:
                    guard.record_failure(entry["provider"], entry.get("model"))
                    logger.warning("%s/%s generation failed: %s", entry["provider"], entry.get("model"), exc)

            parsed_batch = self._parse_json_batch(raw)
            if not parsed_batch:
                parsed_batch = self._generate_fallback_batch(
                    request=request,
                    doc_title=doc_title,
                    topic=topic,
                    n_items=n_items,
                    offset=len(items),
                    target_language=target_language,
                )

            items.extend(parsed_batch)

        return items

    # ---------------------------------------------------------------------------
    # STAGE C: DEDUPLICATION
    # ---------------------------------------------------------------------------
    def _stage_deduplicate(self, items: List[Dict[str, Any]], threshold: float = 0.88) -> List[Dict[str, Any]]:
        unique_items: List[Dict[str, Any]] = []
        for item in items:
            item_text = self._get_item_text(item)
            is_duplicate = False
            for existing in unique_items:
                existing_text = self._get_item_text(existing)
                ratio = difflib.SequenceMatcher(None, item_text.lower(), existing_text.lower()).ratio()
                if ratio >= threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_items.append(item)
        return unique_items

    # ---------------------------------------------------------------------------
    # STAGE D: GROUNDING VERIFICATION
    # ---------------------------------------------------------------------------
    def _stage_verify_grounding(
        self,
        items: List[Dict[str, Any]],
        passages: List[Dict[str, Any]],
        all_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Verifies that each item's citations genuinely correspond to the injected passages.
        Uses top_passages for word-level overlap and all_chunks (when provided) to resolve
        chunk_id references that were generated from the coverage plan but not retrieved by RAG.
        """
        verified = []
        # Build a multi-key passage index so LLM-cited chunk_ids can be resolved even
        # when the exact format differs (e.g. missing _child_N suffix, or coming from
        # metadata vs. top-level id field).
        passage_map: Dict[str, str] = {}
        all_passage_texts: List[str] = []

        # Index all available chunk sets: RAG top passages first, then the full
        # parent chunk set (when provided). This is critical because the LLM is
        # prompted with chunk_ids from the coverage plan (e.g. parent_1) which may
        # differ from the RAG-retrieved IDs (e.g. parent_66).
        chunk_sources = list(passages)
        if all_chunks:
            chunk_sources = chunk_sources + [
                c for c in all_chunks
                if (c.get("id") or c.get("metadata", {}).get("chunk_id", ""))
                not in {p.get("id") or p.get("metadata", {}).get("chunk_id", "") for p in passages}
            ]

        for p in chunk_sources:
            passage_text = (p.get("content") or p.get("text") or "").lower()
            # Only add to all_passage_texts for RAG passages (used for fallback overlap)
            if p in passages:
                all_passage_texts.append(passage_text)

            candidate_ids = set()
            top_id = p.get("id", "")
            if top_id:
                candidate_ids.add(top_id)
            meta_id = p.get("metadata", {}).get("chunk_id", "")
            if meta_id:
                candidate_ids.add(meta_id)

            for cid in list(candidate_ids):
                passage_map[cid] = passage_text
                if "_child_" in cid:
                    passage_map[cid.rsplit("_child_", 1)[0]] = passage_text
                simplified = re.sub(r"[-_]\d+$", "", cid)
                if simplified and simplified != cid:
                    passage_map.setdefault(simplified, passage_text)

        logger.debug(
            "[GROUNDING] passage_map keys (%d): %s",
            len(passage_map),
            list(passage_map.keys())[:20],
        )

        # Pre-compute word sets for all passages (used in fallback matching)
        all_passage_word_sets: List[set] = [
            set(re.findall(r"\w{4,}", t)) for t in all_passage_texts
        ]

        for item in items:
            raw_sources = item.get("fuentes") or item.get("sources")
            if not raw_sources or not isinstance(raw_sources, list):
                item["fuentes"] = []
                item["grounded"] = False
                verified.append(item)
                continue

            valid_sources = []
            for src in raw_sources:
                if not isinstance(src, dict):
                    continue

                chunk_id = src.get("chunk_id", "")
                passage_text = passage_map.get(chunk_id)
                matched_via = "direct" if passage_text else None

                if not passage_text and all_passage_texts:
                    # Use grounding text (factual claims only) for item-word overlap,
                    # so distractors in quiz opciones don't inflate the match.
                    grounding_words = set(re.findall(r"\w{4,}", self._get_grounding_text(item).lower()))
                    best_overlap = 0.0
                    best_text = ""
                    for p_text, p_words in zip(all_passage_texts, all_passage_word_sets):
                        if grounding_words and p_words:
                            overlap = len(grounding_words & p_words) / len(grounding_words)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                best_text = p_text
                    logger.debug(
                        "[GROUNDING] chunk_id=%r → no direct match; best_overlap=%.2f",
                        chunk_id, best_overlap,
                    )
                    if best_overlap >= 0.25:
                        passage_text = best_text
                        matched_via = f"fallback_overlap({best_overlap:.2f})"

                extract = (src.get("extracto") or "").strip().lower()

                is_supported = False
                fails_entity_check = False

                if passage_text:
                    passage_lower = passage_text.lower()

                    # Priority 1: verbatim extract check.
                    # A textually exact citation is proven by definition; skip the
                    # anti-negation and numeric gates entirely — they are designed to
                    # catch paraphrase hallucinations, not verbatim quotes.
                    if extract and (extract in passage_lower or passage_lower in extract):
                        is_supported = True
                        logger.debug(
                            "[GROUNDING] chunk_id=%r verbatim extract matched; bypassing strict gates",
                            chunk_id,
                        )
                    else:
                        # Anti-negation and strict entity validation.
                        # Run on grounding text only (factual claims), NOT on the full
                        # item text that includes distractors in quiz opciones.
                        # Negation / numeric tokens in distractors are intentionally
                        # wrong and must not drive source-chunk requirements.
                        negation_pattern = re.compile(
                            r"\b(no|nunca|jamas|jamás|sin|excepto|neither|nor|not|never|without|except)\b",
                            flags=re.IGNORECASE,
                        )
                        numeric_entities_pattern = re.compile(
                            r"\b\d+([.,]\d+)?\b"
                        )

                        item_grounding_text = self._get_grounding_text(item)
                        item_negations = set(negation_pattern.findall(item_grounding_text.lower()))
                        item_numbers = set(numeric_entities_pattern.findall(item_grounding_text))

                        # 1. Anti-negation check: if item expresses a negation, cited chunk must contain it
                        if item_negations:
                            passage_negations = set(negation_pattern.findall(passage_lower))
                            missing_negations = item_negations - passage_negations
                            if missing_negations:
                                fails_entity_check = True
                                logger.debug(
                                    "[GROUNDING] chunk_id=%r rejected due to missing negation token(s) in chunk: %s",
                                    chunk_id, missing_negations,
                                )

                        # 2. Strict entity/numeric check: if item states specific numeric values, chunk must contain them
                        if not fails_entity_check and item_numbers:
                            passage_numbers = set(re.findall(r"\b\d+([.,]\d+)?\b", passage_text))
                            missing_numbers = item_numbers - passage_numbers
                            if missing_numbers:
                                fails_entity_check = True
                                logger.debug(
                                    "[GROUNDING] chunk_id=%r rejected due to missing numeric token(s) in chunk: %s",
                                    chunk_id, missing_numbers,
                                )

                        if not fails_entity_check:
                            # Extract word-overlap check (paraphrased citation)
                            extract_words = set(re.findall(r"\w{4,}", extract))
                            passage_words = set(re.findall(r"\w{4,}", passage_lower))
                            if extract_words:
                                ew_score = len(extract_words & passage_words) / len(extract_words)
                                logger.debug(
                                    "[GROUNDING] chunk_id=%r extract_word_overlap=%.2f (via %s)",
                                    chunk_id, ew_score, matched_via,
                                )
                                if ew_score >= 0.45:
                                    is_supported = True
                            if not is_supported and not extract:
                                # Last resort: use grounding text words (no distractors)
                                grounding_words = set(re.findall(r"\w{4,}", item_grounding_text.lower()))
                                if grounding_words and passage_words:
                                    iw_score = len(grounding_words & passage_words) / len(grounding_words)
                                    logger.debug(
                                        "[GROUNDING] chunk_id=%r item_word_overlap=%.2f (via %s)",
                                        chunk_id, iw_score, matched_via,
                                    )
                                    if iw_score >= 0.25:
                                        is_supported = True
                elif not passage_text:
                    logger.debug(
                        "[GROUNDING] chunk_id=%r → passage_text empty/missing; no verification possible",
                        chunk_id,
                    )

                logger.debug(
                    "[GROUNDING] src chunk_id=%r is_supported=%s extract_len=%d",
                    chunk_id, is_supported, len(extract),
                )

                clean_src = dict(src)
                pg = clean_src.get("pagina")
                if not isinstance(pg, int) or pg <= 0:
                    clean_src.pop("pagina", None)

                clean_src["verificado"] = is_supported
                valid_sources.append(clean_src)

            item["grounded"] = any(s.get("verificado", False) for s in valid_sources)
            logger.debug(
                "[GROUNDING] item grounded=%s sources=%d",
                item["grounded"], len(valid_sources),
            )
            item["fuentes"] = valid_sources
            verified.append(item)

        return verified

    # ---------------------------------------------------------------------------
    # STAGE E: COMPLETION & REPAIR ROUNDS
    # ---------------------------------------------------------------------------
    def _stage_completion(
        self,
        request: AdaptationRequest,
        doc_title: str,
        topics: List[Dict[str, Any]],
        needed: int,
        existing_items: List[Dict[str, Any]],
        target_language: str = "Spanish",
    ) -> List[Dict[str, Any]]:
        extra = []
        max_idx = len(existing_items)
        for i in range(needed):
            topic = topics[i % len(topics)] if topics else {
                "topic": doc_title, "chunk_id": "chunk-001", "page": 1, "context": doc_title
            }
            extra.append(
                self._generate_fallback_item(
                    request=request,
                    doc_title=doc_title,
                    topic=topic,
                    item_idx=max_idx + i + 1,
                    target_language=target_language,
                )
            )
        return extra

    def _stage_repair_items(
        self,
        request: AdaptationRequest,
        items_to_repair: List[Tuple[int, Dict[str, Any], List[str]]],
        passages: List[Dict[str, Any]],
        all_chunks: Optional[List[Dict[str, Any]]] = None,
        target_language: str = "Spanish",
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """
        Surgically repairs failed items using LLM prompted with specific criticism issues
        and source chunk passages. Executes 1 LLM batch call for the failed items.
        """
        if not items_to_repair:
            return []

        # Build chunk lookup
        chunk_map: Dict[str, str] = {}
        for p in (passages or []):
            cid = p.get("id") or p.get("metadata", {}).get("chunk_id", "")
            if cid:
                chunk_map[cid] = (p.get("content") or p.get("text") or "")[:500]
        if all_chunks:
            for p in all_chunks:
                cid = p.get("id") or p.get("metadata", {}).get("chunk_id", "")
                if cid and cid not in chunk_map:
                    chunk_map[cid] = (p.get("content") or p.get("text") or "")[:500]

        repair_payload = []
        for idx, item, issues in items_to_repair:
            cited_chunks = []
            for s in (item.get("fuentes") or []):
                if isinstance(s, dict):
                    cid = s.get("chunk_id", "")
                    text = chunk_map.get(cid, "")
                    cited_chunks.append({"chunk_id": cid, "text": text})

            repair_payload.append({
                "item_index": idx,
                "current_item": {
                    k: v for k, v in item.items() if k not in ("fuentes", "sources")
                },
                "issues_detected": issues,
                "cited_source_context": cited_chunks,
            })

        system_instruction = (
            "ROLE: Expert Educational Content Repair Specialist.\n"
            "TASK: Surgically correct and rewrite the provided educational items so that "
            "every factual claim is strictly supported by their cited source context. "
            "Resolve all detected issues without changing the educational format.\n"
            f"TARGET LANGUAGE: {target_language}\n"
            "OUTPUT FORMAT: Return strictly a valid JSON array of corrected items, each with "
            "'item_index' (integer matching input) and the corrected item fields."
        )

        prompt = (
            f"Audience Profile: {request.recipient_profile}\n"
            f"Output Format: {request.output_format}\n"
            f"Target Language: {target_language}\n\n"
            "ITEMS TO REPAIR:\n"
            f"{json.dumps(repair_payload, ensure_ascii=False, indent=2)}\n\n"
            "Rewrite each item ensuring 100% fidelity to the cited source context. "
            "Preserve original source citations."
        )

        repaired_map: Dict[int, Dict[str, Any]] = {}
        guard = get_llm_guard()
        raw = None
        fmt_key = getattr(request, "output_format", "flashcards")
        cascade = self.router.get_model_cascade(fmt_key)
        if not cascade:
            cascade = [{"provider": k, "model": None} for k in self.router.get_cascade_order(fmt_key)]
        for entry in cascade:
            llm = self._provider_map.get(entry["provider"])
            if not llm or not llm.is_available or not guard.should_attempt(entry["provider"], entry.get("model")):
                continue
            guard.wait_for_slot(entry["provider"], entry.get("model"))
            try:
                raw = llm.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_output=True,
                    model_name=entry.get("model"),
                )
                if raw:
                    guard.record_success(entry["provider"], entry.get("model"))
                    self._track_model(entry["provider"], entry.get("model"))
                    break
            except Exception as exc:
                guard.record_failure(entry["provider"], entry.get("model"))
                logger.warning("Repair LLM %s failed: %s", entry.get("provider"), exc)

        if raw:
            parsed = self._parse_json_batch(raw)
            if isinstance(parsed, list):
                for p_item in parsed:
                    if isinstance(p_item, dict) and "item_index" in p_item:
                        idx = p_item.get("item_index")
                        clean = {k: v for k, v in p_item.items() if k != "item_index"}
                        repaired_map[idx] = clean

        results = []
        for idx, orig_item, _ in items_to_repair:
            if idx in repaired_map:
                rep = dict(repaired_map[idx])
                # Preserve sources and mark repaired
                if "fuentes" not in rep or not rep["fuentes"]:
                    rep["fuentes"] = orig_item.get("fuentes", [])
                rep["repaired"] = True
                results.append((idx, rep))
            else:
                # Mark original as attempted repair without loop
                orig_copy = dict(orig_item)
                orig_copy["repaired"] = True
                results.append((idx, orig_copy))

        return results

    # ---------------------------------------------------------------------------
    # STAGE F: CRITIC EVALUATION & AUDITING
    # ---------------------------------------------------------------------------
    def _evaluate_quality_with_critic(
        self,
        request: AdaptationRequest,
        generated_items: List[Dict[str, Any]],
        passages: List[Dict[str, Any]],
        fallback_score: float,
        all_chunks: Optional[List[Dict[str, Any]]] = None,
        target_language: str = "Spanish",
    ) -> Tuple[QualityEvaluation, List[Dict[str, Any]]]:
        """
        Uses auditor prompt template to evaluate generated educational items individually,
        identifying grounding issues and unverified claims.
        Builds source_facts from the chunks actually cited by items (not just top RAG passages)
        so the critic evaluates the same context as the heuristic verifier.
        """
        is_spanish = _is_spanish(target_language)
        if not generated_items:
            evaluation = QualityEvaluation(
                source_grounding_score=fallback_score,
                pedagogical_clarity="Alta" if is_spanish else "High",
                observations=(
                    "Verificación de calidad heurística; sin elementos para auditar."
                    if is_spanish
                    else "Heuristic quality verification; no items to audit."
                )
            )
            return evaluation, generated_items

        try:
            auditor_template = load_prompt("auditor.md")

            # Build a lookup from chunk_id → text covering all available chunks.
            # Prioritise content from cited chunks so the critic evaluates the same
            # context the heuristic verifier used, avoiding score/observations contradiction.
            all_chunk_map: Dict[str, str] = {}
            for chunk_list in (passages, all_chunks or []):
                for p in chunk_list:
                    pid = p.get("id") or p.get("metadata", {}).get("chunk_id", "")
                    if pid:
                        all_chunk_map[pid] = (p.get("content") or p.get("text") or "")[:400]

            # Collect chunk_ids cited by the generated items.
            cited_ids: List[str] = []
            seen: set = set()
            for it in generated_items:
                for src in (it.get("fuentes") or []):
                    if isinstance(src, dict):
                        cid = src.get("chunk_id", "")
                        if cid and cid not in seen:
                            seen.add(cid)
                            cited_ids.append(cid)

            # Build source_facts: cited chunks first, then top RAG passages as supplement.
            fact_chunks: List[tuple] = []
            for cid in cited_ids:
                if cid in all_chunk_map:
                    fact_chunks.append((cid, all_chunk_map[cid]))
            # Supplement with RAG top passages not already included
            for p in passages:
                pid = p.get("id") or p.get("metadata", {}).get("chunk_id", "")
                if pid and pid not in seen:
                    fact_chunks.append((pid, (p.get("content") or p.get("text") or "")[:400]))
                if len(fact_chunks) >= 10:
                    break

            source_facts = "\n\n".join(
                f"[{cid}] {text}" for cid, text in fact_chunks
            )
            items_to_audit = [
                {
                    "index": i,
                    "text": self._get_item_text(it),
                    "sources": [s.get("chunk_id") for s in (it.get("fuentes") or []) if isinstance(s, dict)],
                }
                for i, it in enumerate(generated_items)
            ]

            prompt = auditor_template.format(
                recipient_profile=request.recipient_profile,
                target_language=target_language,
                source_facts=source_facts,
                generated_items=json.dumps(items_to_audit, ensure_ascii=False, indent=2),
            )
            system_instruction = (
                "ROLE: Impartial educational auditor and fact-checker. "
                "OUTPUT FORMAT: Return strictly valid JSON object."
            )

            raw = None
            guard = get_llm_guard()
            for entry in settings.CRITIC_CASCADE:
                llm = self._provider_map.get(entry["provider"])
                if not llm or not llm.is_available or not guard.should_attempt(entry["provider"], entry.get("model")):
                    continue
                guard.wait_for_slot(entry["provider"], entry.get("model"))
                try:
                    raw = llm.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        json_output=True,
                        model_name=entry.get("model"),
                    )
                    if raw:
                        self.critic_provider = entry["provider"]
                        # Resolve model name: use entry model or provider default
                        resolved_model = entry.get("model")
                        if not resolved_model:
                            if entry["provider"] == "groq":
                                resolved_model = settings.DEFAULT_GROQ_MODEL
                            elif entry["provider"] == "gemini":
                                resolved_model = settings.DEFAULT_GEMINI_MODEL_FLASH
                            elif entry["provider"] == "openrouter":
                                resolved_model = settings.DEFAULT_OPENROUTER_MODEL
                        self.critic_model = resolved_model
                        self._track_model(entry["provider"], resolved_model or entry.get("model"))
                        guard.record_success(entry["provider"], entry.get("model"))
                        logger.info("Crítico respondió con %s/%s", entry["provider"], resolved_model)
                        break
                except Exception as exc:
                    guard.record_failure(entry["provider"], entry.get("model"))
                    logger.warning("Critic %s/%s failed: %s", entry["provider"], entry.get("model"), exc)
            if not raw:
                logger.warning("Todos los providers del crítico fallaron; usando score automático.")
                self.critic_provider = "evaluador_heuristico"
                self.critic_model = "analizador_anclaje_rag"

            text = raw.strip() if raw else "{}"
            text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)

            # Ensure all items have a stable grounding identifier (_gid)
            for i, it in enumerate(generated_items):
                if "_gid" not in it:
                    it["_gid"] = f"ground_{i}"

            item_evals = data.get("item_evaluations", [])
            flagged_indices = {
                e.get("index") for e in item_evals if e.get("is_grounded") is False
            }

            accepted_items = []
            for i, it in enumerate(generated_items):
                if i in flagged_indices and it.get("grounded") is False:
                    logger.info("Critic rejected ungrounded item %d (%s): %s", i, it.get("_gid"), self._get_item_text(it)[:60])
                else:
                    accepted_items.append(it)

            if not accepted_items:
                accepted_items = generated_items

            clarity_raw = str(data.get("pedagogical_clarity", "High"))
            if is_spanish:
                clarity_map = {"High": "Alta", "Medium": "Media", "Low": "Baja"}
                clarity_val = clarity_map.get(clarity_raw, clarity_raw)
                default_obs = "Validado y evaluado por el agente crítico educativo."
            else:
                clarity_map = {"Alta": "High", "Media": "Medium", "Baja": "Low"}
                clarity_val = clarity_map.get(clarity_raw, clarity_raw)
                default_obs = "Validated and evaluated by the educational critic agent."

            eval_by_index = {
                e.get("index"): e for e in item_evals if isinstance(e, dict) and "index" in e
            }

            per_item_list = []
            for i, it in enumerate(generated_items):
                critic_entry = eval_by_index.get(i, {})
                critic_grounded = critic_entry.get("is_grounded")
                verificado_revisor = bool(critic_grounded is not False)
                verificado_lexico = bool(it.get("grounded", False))
                # Combined criterion: both lexical and critic reviewer approved
                origen_verificado = bool(verificado_lexico and verificado_revisor)

                item_clarity_raw = critic_entry.get("clarity", data.get("pedagogical_clarity", "High"))
                item_clarity = clarity_map.get(str(item_clarity_raw), str(item_clarity_raw))

                item_issues = critic_entry.get("issues", [])
                if not isinstance(item_issues, list):
                    item_issues = [str(item_issues)] if item_issues else []

                per_item_list.append({
                    "index": i,
                    "_gid": it.get("_gid", f"ground_{i}"),
                    "verificado_lexico": verificado_lexico,
                    "verificado_revisor": verificado_revisor,
                    "origen_verificado": origen_verificado,
                    "claridad": item_clarity,
                    "issues": item_issues,
                    "es_fallback": bool(it.get("es_fallback", False)),
                })

            overall_score = float(data.get("overall_grounding_score", fallback_score))
            evaluation = QualityEvaluation(
                source_grounding_score=round(max(0.0, min(1.0, overall_score)), 2),
                pedagogical_clarity=clarity_val,
                observations=str(data.get("observations", default_obs)),
                per_item=per_item_list,
            )
            return evaluation, accepted_items

        except Exception as e:
            logger.warning(f"Critic auditor failed: {e}")
            self.critic_provider = "evaluador_heuristico"
            self.critic_model = "analizador_anclaje_rag"
            for i, it in enumerate(generated_items):
                if "_gid" not in it:
                    it["_gid"] = f"ground_{i}"

            fallback_per_item = [
                {
                    "index": i,
                    "_gid": it.get("_gid", f"ground_{i}"),
                    "verificado_lexico": bool(it.get("grounded", False)),
                    "verificado_revisor": True,
                    "origen_verificado": bool(it.get("grounded", False)),
                    "claridad": "Alta" if is_spanish else "High",
                    "issues": [] if it.get("grounded", False) else ["Sin confirmación léxica contra fragmentos fuente."],
                    "es_fallback": bool(it.get("es_fallback", False)),
                }
                for i, it in enumerate(generated_items)
            ]
            evaluation = QualityEvaluation(
                source_grounding_score=fallback_score,
                pedagogical_clarity="Alta" if is_spanish else "High",
                observations=(
                    "Evaluación heurística de respaldo completada con éxito."
                    if is_spanish
                    else "Heuristic fallback evaluation completed successfully."
                ),
                per_item=fallback_per_item,
            )
            return evaluation, generated_items

    # ---------------------------------------------------------------------------
    # HELPERS & FORMATTING
    # ---------------------------------------------------------------------------
    def _clean_document_title(self, request: AdaptationRequest) -> str:
        doc_title = request.title or getattr(request, "documento_titulo", "Technical Document")
        doc_title = re.sub(r"\.(pdf|md|markdown|txt)$", "", doc_title.strip(), flags=re.IGNORECASE)
        doc_title = re.sub(r"[-_]", " ", doc_title).strip()
        if not doc_title or re.match(r"^\d+(\.\d+)?$", doc_title):
            lines = [
                line.strip()
                for line in (request.content or "").split("\n")
                if len(line.strip()) > 10 and not line.startswith("---")
            ]
            doc_title = lines[0][:60] if lines else "Technical Document"
        return doc_title

    def _compute_request_hash(self, request: AdaptationRequest, doc_title: str, language: str) -> str:
        hash_input = (
            f"{doc_title}:{(request.content or '')[:1000]}:{request.recipient_profile}:"
            f"{request.output_format}:{request.niche}:{request.detail_level}:"
            f"{request.quantity_level}:{request.target_quantity or request.quantity}:{language}"
        )
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    def _calculate_target_quantity(
        self,
        request: AdaptationRequest,
        language: str = "Spanish",
        coverage_plan: Optional[CoveragePlan] = None,
        passages_count: int = 0,
    ) -> Tuple[int, int, Optional[str]]:
        fmt_key = (request.output_format or "flashcards").lower()
        lvl_key = (request.quantity_level or "estandar").lower()

        # Map Spanish format names to canonical keys if needed
        format_canonical_map = {
            "resumen ejecutivo": settings.FORMAT_SUMMARY,
            "guion de clase": settings.FORMAT_CLASS_SCRIPT,
        }
        lookup_fmt = format_canonical_map.get(fmt_key, fmt_key)

        base_target = QUANTITY_TABLE.get(lookup_fmt, {}).get(lvl_key, 20)
        target_quantity = request.target_quantity if request.target_quantity is not None else (
            base_target if request.quantity_level else (request.quantity or base_target)
        )

        if coverage_plan is not None:
            # Use the planner's capacity estimate, which is based on total content
            effective_target = min(target_quantity, coverage_plan.viable_target)
            warning = coverage_plan.capacity_warning if effective_target < target_quantity else None
        else:
            # Legacy fallback when no plan is available
            cap_factor = FORMAT_CAPACITY_FACTOR.get(lookup_fmt, 4)
            max_capacity = max(5, max(1, passages_count) * cap_factor)
            effective_target = min(target_quantity, max_capacity)
            warning = None
            if effective_target < target_quantity:
                warning = get_capacity_warning(effective_target, target_quantity, language=language)

        return target_quantity, effective_target, warning

    def _get_item_primary_text(self, item: Dict[str, Any]) -> str:
        """Extracts the primary question, front, or title of an educational item."""
        return (
            item.get("frente")
            or item.get("pregunta")
            or item.get("titulo")
            or item.get("punto_clave")
            or item.get("narracion")
            or ""
        )

    def _get_item_text(self, item: Dict[str, Any]) -> str:
        """
        Concatenates all text fields of an educational item across supported formats.
        Ensures grounding and critique audit inspect the complete claim (front, back,
        options, correct answer, justification, instruction, example, business impact).
        """
        parts = []
        for key in (
            "frente",
            "dorso",
            "pregunta",
            "respuesta_correcta",
            "justificacion",
            "justificacion_didactica",
            "pista_didactica",
            "titulo",
            "instruccion",
            "ejemplo",
            "narracion",
            "punto_clave",
            "impacto_negocio",
        ):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())

        options = item.get("opciones")
        if isinstance(options, list):
            for opt in options:
                if isinstance(opt, str) and opt.strip():
                    parts.append(opt.strip())

        if not parts:
            primary = self._get_item_primary_text(item)
            return primary if primary else ""

        return " ".join(parts)

    def _get_grounding_text(self, item: Dict[str, Any]) -> str:
        """
        Returns only the factual-claim fields of an educational item for use in
        grounding verification gates (anti-negation and strict numeric entity checks).

        Deliberately excludes:
          - opciones: distractors are intentionally false by design;
            their negations/numbers must not drive source-chunk requirements.
          - pista_didactica, justificacion_didactica, ejemplo: pedagogical aids
            and illustrative pseudo-code, not factual claims about the source.
          - fuentes / sources: citation metadata, not content.

        Format-specific fields included:
          - quiz:      pregunta + respuesta_correcta + justificacion
          - flashcard: frente + dorso
          - tutorial:  titulo + instruccion  (not ejemplo)
          - summary/script: punto_clave + impacto_negocio + narracion
        """
        parts = []
        for key in (
            "frente",
            "dorso",
            "pregunta",
            "respuesta_correcta",
            "justificacion",
            "titulo",
            "instruccion",
            "narracion",
            "punto_clave",
            "impacto_negocio",
        ):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())

        if not parts:
            return self._get_item_text(item)

        return " ".join(parts)

    def _is_garbage_item(self, item: Dict[str, Any], per_item_rec: Optional[Dict[str, Any]] = None) -> bool:
        """
        Detects unusable or garbage items based on clarity, length, and content.
        Criteria:
          1. Empty primary fields (no front, question, title, etc.).
          2. Fewer than 5 useful words in grounding text when the item has a
             recognized format key (frente, pregunta, titulo, etc.).
          3. Explicitly ungrounded combined with Low clarity (Baja/Low).
        Note: items without any recognized format key (e.g., raw test fixtures
        containing only 'fuentes') are exempt from all content-based rules.
        """
        _format_keys = {"frente", "pregunta", "titulo", "paso", "punto_clave", "narracion", "escena"}
        has_format_key = bool(_format_keys.intersection(item.keys()))

        # Only apply content rules to items that carry recognized format fields.
        if not has_format_key:
            return False

        primary = self._get_item_primary_text(item).strip()
        if not primary:
            return True

        # Check for mixed or empty secondary fields when applicable
        if "frente" in item and not str(item.get("dorso", "")).strip():
            return True
        if "pregunta" in item and not str(item.get("respuesta_correcta", "")).strip() and not item.get("opciones"):
            return True

        grounding_text = self._get_grounding_text(item).strip()
        word_count = len(grounding_text.split())

        # Low clarity combined with ungrounded verdict
        if per_item_rec:
            clarity = str(per_item_rec.get("claridad", ""))
            revisor_ok = per_item_rec.get("verificado_revisor", True)
            lexical_ok = per_item_rec.get("verificado_lexico", False)
            if clarity in ("Baja", "Low") and (not revisor_ok or not lexical_ok):
                return True

        # Discard items where the grounding text is trivially short (< 5 words),
        # indicating empty or meaningless content (e.g. frente="Hola", dorso="Mundo").
        if word_count < 5:
            return True

        return False

    def _parse_json_batch(self, raw: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        if not raw:
            return None
        text = raw.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # First attempt parsing raw JSON directly (handles objects or arrays)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                # Check for common wrapper keys like "items", "quiz", "flashcards", etc.
                for key in ("items", "elementos", "quiz", "flashcards", "preguntas", "data"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
                # If any dict value is a list of dicts, return the first one found
                for val in parsed.values():
                    if isinstance(val, list) and (not val or isinstance(val[0], dict)):
                        return val
        except Exception:
            pass

        # Fallback to extracting array substring between '[' and ']'
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return None

    def _generate_fallback_batch(
        self,
        request: AdaptationRequest,
        doc_title: str,
        topic: Dict[str, Any],
        n_items: int,
        offset: int,
        target_language: str = "Spanish",
    ) -> List[Dict[str, Any]]:
        return [
            self._generate_fallback_item(
                request=request,
                doc_title=doc_title,
                topic=topic,
                item_idx=offset + i + 1,
                target_language=target_language,
            )
            for i in range(n_items)
        ]

    def _generate_fallback_item(
        self,
        request: AdaptationRequest,
        doc_title: str,
        topic: Dict[str, Any],
        item_idx: int,
        target_language: str = "Spanish",
    ) -> Dict[str, Any]:
        fmt = request.output_format.lower()
        topic_name = topic["topic"]
        raw_concept = topic.get("concept", topic_name.split("(")[0].strip())

        # Clean concept of any trailing PDF xref or startxref artifacts
        clean_concept = re.sub(r"(?:%?\s*startxref[\s\d]*|%%EOF|xref\s*\d+\s*\d+|\b\d{5,}\b)", "", raw_concept, flags=re.IGNORECASE).strip()
        clean_concept = re.sub(r"[\:\%\-_]+$", "", clean_concept).strip()
        main_concept = clean_concept if len(clean_concept) > 2 else "Componente Técnico"

        context = topic.get("context", "")
        is_spanish = _is_spanish(target_language)

        # Avoid redundant phrasing when topic and concept share the same text
        topic_clean = topic_name.strip()
        concept_clean = main_concept.strip()
        if not topic_clean or topic_clean.lower() == concept_clean.lower() or concept_clean.lower() in topic_clean.lower():
            topic_context_es = ""
            topic_context_en = ""
        else:
            topic_context_es = f" en el marco de {topic_clean}"
            topic_context_en = f" in the context of {topic_clean}"

        sentences = [s.strip() for s in re.split(r"[.!?]", context) if len(s.strip()) > 15]
        if sentences:
            target_sentence = sentences[item_idx % len(sentences)]
        else:
            target_sentence = (
                f"Definición clave y principios fundamentales de {main_concept}."
                if is_spanish
                else f"Key definition and fundamental principles of {main_concept}."
            )

        # Provide reference citation but clearly mark provenance without fabricating similarity scores
        fuente: Dict[str, Any] = {
            "chunk_id": topic.get("chunk_id", "chunk-001"),
            "extracto": target_sentence[:100],
            "tipo_fuente": "contexto_estructural",
            "es_fallback": True,
        }
        if topic.get("section"):
            fuente["seccion"] = topic["section"]
        if topic.get("breadcrumb"):
            fuente["breadcrumb"] = topic["breadcrumb"]
        page_val = topic.get("page")
        if isinstance(page_val, int) and page_val > 0:
            fuente["pagina"] = page_val

        res_item: Dict[str, Any]
        if "flashcard" in fmt:
            if is_spanish:
                res_item = {
                    "frente": f"¿Cuál es el propósito y la aplicación de '{main_concept}'{topic_context_es}?",
                    "dorso": f"{target_sentence} Optimiza el rendimiento, la mantenibilidad y la robustez técnica en el entorno de {request.niche}.",
                    "pista_didactica": f"Pista: Evalúa el impacto operativo directo de {main_concept}.",
                    "fuentes": [fuente],
                }
            else:
                res_item = {
                    "frente": f"What is the purpose and application of '{main_concept}'{topic_context_en}?",
                    "dorso": f"{target_sentence} Optimizes performance and robustness in {request.niche}.",
                    "pista_didactica": f"Hint: Assess the operational impact of {main_concept}.",
                    "fuentes": [fuente],
                }
        elif "quiz" in fmt:
            if is_spanish:
                res_item = {
                    "pregunta": f"Respecto a {main_concept}{topic_context_es}, ¿cuál de las siguientes afirmaciones es correcta según la documentación?",
                    "opciones": [
                        f"{target_sentence}",
                        f"Invalida las políticas técnicas y de seguridad estándar en {request.niche}.",
                        f"Aplica únicamente a entornos heredados (legacy) en desuso.",
                        f"Carece de relevancia para las funciones de {request.recipient_profile}.",
                    ],
                    "respuesta_correcta": f"{target_sentence}",
                    "justificacion": f"Fundamentado directamente en el texto fuente: '{target_sentence[:120]}'",
                    "justificacion_didactica": f"Concepto medular para el desarrollo de competencias en {request.recipient_profile}.",
                    "fuentes": [fuente],
                }
            else:
                res_item = {
                    "pregunta": f"Regarding {main_concept}{topic_context_en}, which of the following statements is correct?",
                    "opciones": [
                        f"{target_sentence}",
                        f"Overrides {request.niche} policies.",
                        f"Applies only to legacy {topic_name} environments.",
                        f"Is unrelated to the requirements of {request.recipient_profile}.",
                    ],
                    "respuesta_correcta": f"{target_sentence}",
                    "justificacion": f"Directly supported by the source text: '{target_sentence[:120]}'",
                    "justificacion_didactica": f"Core technical foundation for {request.recipient_profile}.",
                    "fuentes": [fuente],
                }
        elif "tutorial" in fmt:
            if is_spanish:
                res_item = {
                    "paso": item_idx,
                    "titulo": f"Configuración y aplicación de {main_concept}",
                    "instruccion": f"Implementar {main_concept} siguiendo las directrices técnicas: {target_sentence}",
                    "ejemplo": f"// Ejemplo de configuración práctica para {main_concept}\nejecutar_accion('{main_concept}')",
                    "fuentes": [fuente],
                }
            else:
                res_item = {
                    "paso": item_idx,
                    "titulo": f"Configuring {main_concept}",
                    "instruccion": f"Implement {main_concept} following guidelines: {target_sentence}",
                    "ejemplo": f"// Configuration example for {main_concept}\napply_rule('{main_concept}')",
                    "fuentes": [fuente],
                }
        else:
            if is_spanish:
                res_item = {
                    "punto_clave": f"{main_concept}: {target_sentence}",
                    "impacto_negocio": f"Garantiza la continuidad operativa y eficiencia técnica en el sector {request.niche}.",
                    "fuentes": [fuente],
                }
            else:
                res_item = {
                    "punto_clave": f"{main_concept}: {target_sentence}",
                    "impacto_negocio": f"Ensures operational efficiency and strategic value in {request.niche}.",
                    "fuentes": [fuente],
                }

        res_item["es_fallback"] = True
        return res_item

    def _shuffle_quiz_options(self, items: List[Dict[str, Any]]) -> None:
        """Randomizes where the correct option sits in every quiz item.

        The LLM (and the deterministic fallback generator) both tend to emit
        `respuesta_correcta` as the first option, which clustered correct
        answers in A/B. The renderer matches the answer by string equality
        rather than by index, so reordering `opciones` is safe and leaves the
        question, the justification and the sources untouched.
        """
        for item in items:
            options = item.get("opciones")
            correct = item.get("respuesta_correcta")
            if not isinstance(options, list) or len(options) < 2:
                continue
            if not isinstance(correct, str) or correct not in options:
                continue
            random.shuffle(options)
            item["opciones"] = options

    def _format_adapted_content(
        self,
        request: AdaptationRequest,
        doc_title: str,
        items: List[Dict[str, Any]],
        effective_count: int,
        target_language: str = "Spanish",
    ) -> AdaptedContent:
        fmt = request.output_format.lower()
        is_spanish = _is_spanish(target_language)

        intro = get_contextualized_intro(
            doc_title=doc_title,
            effective_count=effective_count,
            recipient_profile=request.recipient_profile,
            niche=request.niche,
            language=target_language,
        )

        title_template = TITLE_TEMPLATES_ES.get(
            fmt, "Contenido Educativo ({count} Elementos): {doc_title}" if is_spanish else "Educational Content ({count} Items): {doc_title}"
        )
        final_title = title_template.format(count=effective_count, doc_title=doc_title)

        if "quiz" in fmt:
            # Reorder before building QuizItem so `items` and `quizzes` agree.
            self._shuffle_quiz_options(items)
            default_justif = "Fundamento técnico verificado." if is_spanish else "Core technical foundation."
            quizzes = [
                QuizItem(
                    question=it.get("pregunta", f"Pregunta #{i+1}"),
                    options=it.get("opciones", ["A", "B", "C", "D"]),
                    correct_answer=it.get("respuesta_correcta", "A"),
                    didactic_justification=it.get("justificacion_didactica") or it.get("justificacion") or default_justif,
                    sources=[RagFuente(**f) if isinstance(f, dict) else f for f in (it.get("fuentes") or [])],
                )
                for i, it in enumerate(items)
            ]
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                items=items,
                quizzes=quizzes,
            )
        elif "tutorial" in fmt:
            _step_prefix = re.compile(r"^(?:paso|step)\s*\d+[\s:\.\-]+", re.IGNORECASE)
            for i, it in enumerate(items):
                # Enforce 1-based sequential step numbering
                it["paso"] = i + 1
                # Strip any "Paso X:" / "Step X:" prefix from titulo (LLM or fallback)
                raw_tit = str(it.get("titulo") or "").strip()
                while _step_prefix.match(raw_tit):
                    raw_tit = _step_prefix.sub("", raw_tit).strip()
                it["titulo"] = raw_tit or (f"Módulo {i + 1}" if is_spanish else f"Module {i + 1}")

            sections = [
                {
                    "encabezado": (
                        f"Paso {it['paso']}: {it['titulo']}"
                        if is_spanish
                        else f"Step {it['paso']}: {it['titulo']}"
                    ),
                    "contenido": f"{it.get('instruccion', '')}\n\n{it.get('ejemplo', '')}".strip(),
                }
                for it in items
            ]
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                items=items,
                tutorial_sections=sections,
            )
        elif "resumen" in fmt:
            summary_bullets = [
                f"{i+1}. {it.get('punto_clave', 'Punto ' + str(i+1) if is_spanish else 'Point ' + str(i+1))}: {it.get('impacto_negocio', '')}"
                for i, it in enumerate(items)
            ]
            header = f"RESUMEN EJECUTIVO ({effective_count} PUNTOS):" if is_spanish else f"EXECUTIVE SUMMARY ({effective_count} POINTS):"
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                executive_summary=f"{header}\n\n" + "\n".join(summary_bullets),
                items=items,
            )
        elif "guion" in fmt or "clase" in fmt or "script" in fmt:
            for i, it in enumerate(items):
                # Enforce 1-based sequential scene numbering
                it["escena"] = i + 1
                # Strip markdown header artifacts from narration
                if "narracion" in it and isinstance(it["narracion"], str):
                    it["narracion"] = re.sub(r"^(?:#{1,6}\s*|\*{1,2})", "", it["narracion"]).strip()
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                items=items,
            )
        else:
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                items=items,
            )

    _PROVIDER_SHORT = {"gemini": "google", "groq": "groq", "openrouter": "openrouter"}

    def _track_model(self, provider: str, model: Optional[str]) -> None:
        if model:
            self._models_used.setdefault(provider, set()).add(model)

    def _format_models_used(self) -> str:
        parts = []
        for provider in sorted(self._models_used):
            label = self._PROVIDER_SHORT.get(provider, provider)
            parts.append(f"{label}({len(self._models_used[provider])})")
        return ", ".join(parts)

    def _format_models_detail(self) -> List[str]:
        """Flat 'provider/model' list with every LLM used during this run."""
        detail: List[str] = []
        for provider in sorted(self._models_used):
            label = self._PROVIDER_SHORT.get(provider, provider)
            for model in sorted(self._models_used[provider]):
                detail.append(f"{label}/{model}")
        return detail

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
