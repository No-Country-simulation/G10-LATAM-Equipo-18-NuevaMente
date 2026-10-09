"""
agent_orchestrator.py

Purpose:
    Multi-stage agentic pipeline for educational content adaptation.
    Orchestrates document coverage planning, batch content generation with LLMs,
    deduplication, source citation verification, and capacity capping.
    Integrates external prompt templates and multilingual output support.

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
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.labels import (
    FORMAT_LABELS_ES,
    PROFILE_LABELS_ES,
    TITLE_TEMPLATES_ES,
    get_capacity_warning,
    get_capacity_warning_es,
    get_contextualized_intro,
)
from app.infrastructure.llm import GeminiClient, GroqClient, OpenRouterClient
from app.prompts.prompt_loader import load_prompt
from app.schemas.adaptation import (
    AdaptationRequest,
    AdaptationResponse,
    AdaptedContent,
    FlashcardItem,
    OCIStorageResult,
    QualityEvaluation,
    QuizItem,
    RagFuente,
    ResponseMetadata,
)
from app.services.coverage_planner import CoveragePlan, CoveragePlanner, SectionPlan
from app.services.document_storage_service import get_document_storage
from app.services.multi_agent_router import MultiAgentRouter
from app.services.pdf_export_service import PDFExportService

logger = logging.getLogger("AgentOrchestrator")


def _is_spanish(target_language: Optional[str]) -> bool:
    """Returns True if the target language is Spanish (default), False otherwise."""
    if not target_language:
        return True
    lang = target_language.strip().lower()
    return lang.startswith("es") or "span" in lang


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


class AgentOrchestrator:
    """Orchestrates multi-stage agentic adaptation pipeline."""

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
        self.router = MultiAgentRouter()
        self.storage = get_document_storage()
        self._response_cache: Dict[str, AdaptationResponse] = {}

    async def run_pipeline(
        self,
        request: AdaptationRequest,
        top_passages: List[Dict[str, Any]],
        key_concepts: List[str],
        prerequisites: List[str],
        tracer: Optional[Any] = None,
        all_parent_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> AdaptationResponse:
        """Executes full multi-stage pipeline with coverage planning, batching, deduplication, and RAG grounding."""
        doc_title = self._clean_document_title(request)
        target_language = request.language or settings.DEFAULT_OUTPUT_LANGUAGE

        prompt_hash = self._compute_request_hash(request, doc_title, target_language)
        force_regenerate = getattr(request, "force_regenerate", False) or getattr(request, "forzar_regenerar", False)
        if not force_regenerate and prompt_hash in self._response_cache:
            cached_resp = self._response_cache[prompt_hash]
            cached_resp.metadata.origin = "cache"
            cached_resp.metadata.prompt_hash = prompt_hash
            if tracer:
                cached_resp.metadata.timings = {"cache": tracer.total_elapsed_ms()}
                cached_resp.metadata.llm_calls = tracer.llm_calls
            return cached_resp

        # Resolve intended target quantity considering quantity level and explicit overrides
        fmt_key = (request.output_format or "flashcards").lower()
        lvl_key = (request.quantity_level or "estandar").lower()
        format_canonical_map = {
            "resumen ejecutivo": settings.FORMAT_SUMMARY,
            "guion de clase": settings.FORMAT_CLASS_SCRIPT,
        }
        lookup_fmt = format_canonical_map.get(fmt_key, fmt_key)
        base_target = QUANTITY_TABLE.get(lookup_fmt, {}).get(lvl_key, 20)
        requested_count = request.target_quantity if request.target_quantity is not None else (
            base_target if request.quantity_level else (request.quantity or base_target)
        )

        # Build document coverage plan using full parent chunk set when available
        chunks_for_planning = all_parent_chunks or top_passages
        coverage_plan = CoveragePlanner().plan(
            parent_chunks=chunks_for_planning,
            output_format=request.output_format or "flashcards",
            requested_items=requested_count,
            language=target_language,
        )

        target_quantity, effective_target, capacity_warning = self._calculate_target_quantity(
            request=request,
            coverage_plan=coverage_plan,
            language=target_language,
        )

        if tracer:
            tracer.start_stage("planificador")
        topics = self._stage_planner(
            doc_title=doc_title,
            key_concepts=key_concepts,
            coverage_plan=coverage_plan,
            target=effective_target,
            target_language=target_language,
        )
        if tracer:
            tracer.end_stage("planificador")
            tracer.record_llm_call("planificar")

        if tracer:
            tracer.start_stage("generacion_lotes")
        raw_items = self._stage_batch_generators(
            request=request,
            doc_title=doc_title,
            topics=topics,
            passages=top_passages,
            target=effective_target,
            target_language=target_language,
            tracer=tracer,
        )
        if tracer:
            tracer.end_stage("generacion_lotes")

        if tracer:
            tracer.start_stage("deduplicacion")
        dedup_items = self._stage_deduplicate(raw_items)
        if tracer:
            tracer.end_stage("deduplicacion")

        if tracer:
            tracer.start_stage("verificacion_anclaje")
        verified_items = self._stage_verify_grounding(dedup_items, top_passages)
        if tracer:
            tracer.end_stage("verificacion_anclaje")

        # Evaluate quality and factual grounding with the critic/auditor
        grounded_count = sum(1 for it in verified_items if it.get("grounded", False))
        preliminary_score = round(min(1.0, grounded_count / max(1, len(verified_items))), 2)

        evaluation, audited_items = self._evaluate_quality_with_critic(
            request=request,
            generated_items=verified_items,
            passages=top_passages,
            fallback_score=preliminary_score,
        )

        # If items were dropped by the auditor, attempt completion only when the
        # coverage plan confirmed sufficient capacity — otherwise skip to avoid fabrication.
        if len(audited_items) < effective_target and coverage_plan.total_capacity > len(audited_items):
            needed = effective_target - len(audited_items)
            extra_items = self._stage_completion(
                request=request,
                doc_title=doc_title,
                topics=topics,
                needed=needed,
                existing_items=audited_items,
                target_language=target_language,
            )
            for extra in extra_items:
                if len(audited_items) < effective_target:
                    audited_items.append(extra)

        final_items = audited_items[:effective_target]
        items_generated = len(final_items)

        if tracer:
            tracer.start_stage("serializacion_respuesta")
        adapted_content = self._format_adapted_content(
            request=request,
            doc_title=doc_title,
            items=final_items,
            effective_count=items_generated,
            target_language=target_language,
        )
        if tracer:
            tracer.end_stage("serializacion_respuesta")

        # True grounding score reflects genuinely supported items
        verified_citations = sum(1 for it in final_items if any(s.get("verificado", False) for s in (it.get("fuentes") or [])))
        grounding_score = round(min(1.0, verified_citations / max(1, items_generated)), 2)
        evaluation.source_grounding_score = grounding_score

        metadata = ResponseMetadata(
            profile_applied=request.recipient_profile,
            format_generated=request.output_format,
            niche_sector=request.niche,
            detail_level=request.detail_level,
            quantity_level=request.quantity_level,
            requested_items=target_quantity,
            generated_items=items_generated,
            quantity_warning=capacity_warning,
            estimated_study_time_minutes=max(3, items_generated * 2),
            key_concepts=key_concepts[:8],
            prerequisites=prerequisites[:5],
            llm_provider=self.last_provider,
            timings=tracer.timings if tracer else {},
            llm_calls=tracer.llm_calls if tracer else {},
        )

        object_name = (
            f"contenido-{self._slugify(doc_title)[:20]}-"
            f"{self._slugify(request.recipient_profile)[:15]}-{int(time.time())}.json"
        )

        response_payload = {
            "status": "exito",
            "metadatos": metadata.model_dump(by_alias=True),
            "contenido_adaptado": adapted_content.model_dump(by_alias=True),
            "evaluacion_calidad": evaluation.model_dump(by_alias=True),
        }

        storage_info = self.storage.upload_json_artifact(
            object_name=object_name,
            json_data=response_payload,
        )

        storage_result = OCIStorageResult(
            bucket=storage_info["bucket"],
            object_id=storage_info["objeto_id"],
            upload_status=storage_info["status_upload"],
        )

        pdf_path = None
        try:
            pdf_service = PDFExportService()
            output_name = f"scratch/{object_name.replace('.json', '.pdf')}"
            pdf_path = pdf_service.generate_pdf(content=adapted_content, output_path=output_name)
        except Exception as e:
            logger.warning(f"Error generando PDF: {e}")

        final_response = AdaptationResponse(
            status="exito",
            metadata=metadata,
            adapted_content=adapted_content,
            quality_evaluation=evaluation,
            oci_storage=storage_result,
        )
        self._response_cache[prompt_hash] = final_response
        return final_response

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

            writer_system_tmpl = load_prompt("writer_system.md")
            system_instruction = writer_system_tmpl.format(
                niche=request.niche,
                recipient_profile=request.recipient_profile,
                target_language=target_language,
            )

            raw = None
            if tracer:
                tracer.record_llm_call("generar")

            # Dynamically resolve fallback cascade order based on format
            cascade_keys = self.router.get_cascade_order(fmt_key)
            llm_cascade = [self._provider_map[k] for k in cascade_keys if k in self._provider_map]

            # Cascade: attempt each LLM provider in order until one succeeds
            for llm in llm_cascade:
                if not llm.is_available:
                    continue
                try:
                    raw = llm.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        json_output=True,
                    )
                    if raw:
                        self.last_provider = type(llm).__name__.lower().replace("client", "")
                        break
                except Exception as exc:
                    logger.warning("%s generation failed: %s", type(llm).__name__, exc)

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
        self, items: List[Dict[str, Any]], passages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Verifies that each item's citations genuinely correspond to the injected passages.
        Does not fabricate artificial sources or scores when grounding is absent.
        """
        verified = []
        passage_map = {
            p.get("id") or p.get("metadata", {}).get("chunk_id", ""): (
                p.get("content") or p.get("text") or ""
            ).lower()
            for p in passages
        }

        for item in items:
            raw_sources = item.get("fuentes") or item.get("sources")
            if not raw_sources or not isinstance(raw_sources, list):
                # Do not assign fake sources or fabricated similarity scores
                item["fuentes"] = []
                item["grounded"] = False
                verified.append(item)
                continue

            valid_sources = []
            for src in raw_sources:
                if not isinstance(src, dict):
                    continue

                chunk_id = src.get("chunk_id", "")
                passage_text = passage_map.get(chunk_id, "")
                extract = (src.get("extracto") or "").strip().lower()

                # Genuine verification: check if excerpt exists in or substantially overlaps the passage
                is_supported = False
                if passage_text:
                    if extract and (extract in passage_text or passage_text in extract):
                        is_supported = True
                    else:
                        # Check lexical word-set overlap
                        extract_words = set(re.findall(r"\w{4,}", extract))
                        passage_words = set(re.findall(r"\w{4,}", passage_text))
                        if extract_words and len(extract_words & passage_words) / len(extract_words) >= 0.5:
                            is_supported = True
                        elif not extract:
                            # If no explicit extract was given but chunk_id matched, verify topic words
                            item_words = set(re.findall(r"\w{4,}", self._get_item_text(item).lower()))
                            if item_words and len(item_words & passage_words) / len(item_words) >= 0.3:
                                is_supported = True

                # Clean page numbers
                clean_src = dict(src)
                p = clean_src.get("pagina")
                if not isinstance(p, int) or p <= 0:
                    clean_src.pop("pagina", None)

                # Set verified flag on source
                clean_src["verificado"] = is_supported
                valid_sources.append(clean_src)

            item["fuentes"] = valid_sources
            item["grounded"] = any(s.get("verificado", False) for s in valid_sources)
            verified.append(item)

        return verified

    # ---------------------------------------------------------------------------
    # STAGE E: COMPLETION ROUND
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

    # ---------------------------------------------------------------------------
    # STAGE F: CRITIC EVALUATION & AUDITING
    # ---------------------------------------------------------------------------
    def _evaluate_quality_with_critic(
        self,
        request: AdaptationRequest,
        generated_items: List[Dict[str, Any]],
        passages: List[Dict[str, Any]],
        fallback_score: float,
    ) -> Tuple[QualityEvaluation, List[Dict[str, Any]]]:
        """
        Uses auditor prompt template to evaluate generated educational items individually,
        identifying grounding issues and unverified claims.
        """
        if not self.groq_client.is_available or not generated_items:
            evaluation = QualityEvaluation(
                source_grounding_score=fallback_score,
                pedagogical_clarity="High",
                observations="Heuristic quality verification; critic provider unavailable."
            )
            return evaluation, generated_items

        try:
            auditor_template = load_prompt("auditor.md")
            source_facts = "\n\n".join(
                f"[{p.get('id') or p.get('metadata', {}).get('chunk_id', f'chunk-{i+1}')}] "
                f"{(p.get('content') or p.get('text') or '')[:400]}"
                for i, p in enumerate(passages[:6])
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
                source_facts=source_facts,
                generated_items=json.dumps(items_to_audit, ensure_ascii=False, indent=2),
            )
            system_instruction = (
                "ROLE: Impartial educational auditor and fact-checker. "
                "OUTPUT FORMAT: Return strictly valid JSON object."
            )

            raw = self.groq_client.generate(prompt=prompt, system_instruction=system_instruction, json_output=True)
            text = raw.strip() if raw else "{}"
            text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)

            item_evals = data.get("item_evaluations", [])
            flagged_indices = {
                e.get("index") for e in item_evals if e.get("is_grounded") is False
            }

            accepted_items = []
            for i, it in enumerate(generated_items):
                if i in flagged_indices and it.get("grounded") is False:
                    logger.info("Critic rejected ungrounded item %d: %s", i, self._get_item_text(it)[:60])
                else:
                    accepted_items.append(it)

            if not accepted_items:
                accepted_items = generated_items

            overall_score = float(data.get("overall_grounding_score", fallback_score))
            evaluation = QualityEvaluation(
                source_grounding_score=round(max(0.0, min(1.0, overall_score)), 2),
                pedagogical_clarity=str(data.get("pedagogical_clarity", "High")),
                observations=str(data.get("observations", "Evaluated by educational auditor agent."))
            )
            return evaluation, accepted_items

        except Exception as e:
            logger.warning(f"Critic auditor failed: {e}")
            evaluation = QualityEvaluation(
                source_grounding_score=fallback_score,
                pedagogical_clarity="High",
                observations="Heuristic fallback evaluation due to critic agent error."
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

    def _get_item_text(self, item: Dict[str, Any]) -> str:
        return (
            item.get("frente")
            or item.get("pregunta")
            or item.get("titulo")
            or item.get("punto_clave")
            or item.get("narracion")
            or ""
        )

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
        main_concept = topic.get("concept", topic_name.split("(")[0].strip())
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

        if "flashcard" in fmt:
            if is_spanish:
                return {
                    "frente": f"¿Cuál es el propósito y la aplicación de '{main_concept}'{topic_context_es}?",
                    "dorso": f"{target_sentence} Optimiza el rendimiento, la mantenibilidad y la robustez técnica en el entorno de {request.niche}.",
                    "pista_didactica": f"Pista: Evalúa el impacto operativo directo de {main_concept}.",
                    "fuentes": [fuente],
                }
            return {
                "frente": f"What is the purpose and application of '{main_concept}'{topic_context_en}?",
                "dorso": f"{target_sentence} Optimizes performance and robustness in {request.niche}.",
                "pista_didactica": f"Hint: Assess the operational impact of {main_concept}.",
                "fuentes": [fuente],
            }
        elif "quiz" in fmt:
            if is_spanish:
                return {
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
            return {
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
                return {
                    "paso": item_idx,
                    "titulo": f"Paso {item_idx}: Configuración y aplicación de {main_concept}",
                    "instruccion": f"Implementar {main_concept} siguiendo las directrices técnicas: {target_sentence}",
                    "ejemplo": f"// Ejemplo de configuración práctica para {main_concept}\nejecutar_accion('{main_concept}')",
                    "fuentes": [fuente],
                }
            return {
                "paso": item_idx,
                "titulo": f"Step {item_idx}: Configuring {main_concept}",
                "instruccion": f"Implement {main_concept} following guidelines: {target_sentence}",
                "ejemplo": f"// Configuration example for {main_concept}\napply_rule('{main_concept}')",
                "fuentes": [fuente],
            }
        else:
            if is_spanish:
                return {
                    "punto_clave": f"{main_concept}: {target_sentence}",
                    "impacto_negocio": f"Garantiza la continuidad operativa y eficiencia técnica en el sector {request.niche}.",
                    "fuentes": [fuente],
                }
            return {
                "punto_clave": f"{main_concept}: {target_sentence}",
                "impacto_negocio": f"Ensures operational efficiency and strategic value in {request.niche}.",
                "fuentes": [fuente],
            }

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
            sections = [
                {
                    "encabezado": (
                        f"Paso {it.get('paso', i+1)}: {it.get('titulo', f'Módulo {i+1}')}"
                        if is_spanish
                        else f"Step {it.get('paso', i+1)}: {it.get('titulo', f'Module {i+1}')}"
                    ),
                    "contenido": f"{it.get('instruccion', '')}\n\n{it.get('ejemplo', '')}".strip(),
                }
                for i, it in enumerate(items)
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
        else:
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                items=items,
            )

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
