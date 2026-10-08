"""
agent_orchestrator.py

Purpose:
    Multi-stage agentic pipeline for educational content adaptation.
    Orchestrates topic planning, batch content generation with LLMs,
    deduplication, source citation verification, and capacity capping.
    Integrates external prompt templates and multilingual output support.

Input:
    - request (AdaptationRequest): user customization preferences and constraints.
    - top_passages (List[Dict[str, Any]]): RAG-retrieved document parent/child context.
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
    get_capacity_warning_es,
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
from app.services.document_storage_service import get_document_storage
from app.services.multi_agent_router import MultiAgentRouter
from app.services.pdf_export_service import PDFExportService

logger = logging.getLogger("AgentOrchestrator")

QUANTITY_TABLE: Dict[str, Dict[str, int]] = {
    "flashcards": {"breve": 10, "estandar": 20, "amplio": 40, "exhaustivo": 80},
    "quiz": {"breve": 5, "estandar": 10, "amplio": 20, "exhaustivo": 30},
    "tutorial": {"breve": 4, "estandar": 8, "amplio": 15, "exhaustivo": 25},
    "resumen ejecutivo": {"breve": 3, "estandar": 5, "amplio": 10, "exhaustivo": 15},
    "guion de clase": {"breve": 3, "estandar": 5, "amplio": 8, "exhaustivo": 12},
}

FORMAT_CAPACITY_FACTOR: Dict[str, int] = {
    "flashcards": 8,
    "quiz": 4,
    "tutorial": 3,
    "resumen ejecutivo": 2,
    "guion de clase": 2,
}


class AgentOrchestrator:
    """Orchestrates multi-stage agentic adaptation pipeline."""

    def __init__(self):
        self.gemini_client = GeminiClient()
        self.groq_client = GroqClient()
        self.openrouter_client = OpenRouterClient()
        # Ordered cascade: Gemini -> Groq -> OpenRouter (Mistral) -> fallback
        self._llm_cascade = [self.gemini_client, self.groq_client, self.openrouter_client]
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
    ) -> AdaptationResponse:
        """Executes full multi-stage pipeline with batching, deduplication, and RAG grounding."""
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

        target_quantity, effective_target, capacity_warning = self._calculate_target_quantity(
            request=request, passages_count=len(top_passages)
        )

        if tracer:
            tracer.start_stage("planificador")
        topics = self._stage_planner(doc_title, key_concepts, top_passages, effective_target)
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

        if len(verified_items) < effective_target:
            needed = effective_target - len(verified_items)
            extra_items = self._stage_completion(
                request=request,
                doc_title=doc_title,
                topics=topics,
                needed=needed,
                existing_items=verified_items,
            )
            for extra in extra_items:
                if len(verified_items) < effective_target:
                    verified_items.append(extra)

        final_items = verified_items[:effective_target]
        items_generated = len(final_items)

        if tracer:
            tracer.start_stage("serializacion_respuesta")
        adapted_content = self._format_adapted_content(
            request=request,
            doc_title=doc_title,
            items=final_items,
            effective_count=items_generated,
        )
        if tracer:
            tracer.end_stage("serializacion_respuesta")

        verified_citations = sum(1 for it in final_items if it.get("fuentes") or it.get("sources"))
        grounding_score = round(min(1.0, verified_citations / max(1, items_generated)), 2)

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

        evaluation = self._evaluate_quality_with_critic(
            request=request,
            generated_items=final_items,
            passages=top_passages,
            fallback_score=grounding_score,
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
        self, doc_title: str, key_concepts: List[str], passages: List[Dict[str, Any]], target: int
    ) -> List[Dict[str, Any]]:
        topics = []
        if key_concepts:
            base_concepts = key_concepts
        else:
            # Derive pedagogical concepts directly from passage section titles or breadcrumbs.
            extracted = []
            for p in passages:
                title = p.get("title") or p.get("metadata", {}).get("section_title")
                breadcrumb = p.get("breadcrumb") or p.get("metadata", {}).get("breadcrumb")
                cand = title or breadcrumb
                if cand and cand not in extracted:
                    extracted.append(cand)
            base_concepts = extracted if extracted else [doc_title]

        num_topics = max(3, min(15, math.ceil(target / 4)))
        items_per_topic = math.ceil(target / num_topics)

        for i in range(num_topics):
            concept = base_concepts[i % len(base_concepts)]
            passage = passages[i % len(passages)] if passages else {}
            chunk_id = passage.get("id") or passage.get("metadata", {}).get("chunk_id", f"chunk-{i+1}")
            # Only carry page_number when the passage comes from a paged source (PDF);
            # Markdown/TXT sections do not have physical pages.
            raw_page = passage.get("metadata", {}).get("page_number")
            page = raw_page if isinstance(raw_page, int) and raw_page > 0 else None
            section = passage.get("title") or passage.get("metadata", {}).get("section_title")
            breadcrumb = passage.get("breadcrumb") or passage.get("metadata", {}).get("breadcrumb")
            context_snippet = (passage.get("content") or passage.get("text") or doc_title)[:settings.RAG_CONTEXT_SNIPPET_SIZE]

            topics.append({
                "topic": f"{concept} (Parte {i+1})",
                "concept": concept,
                "target_items": items_per_topic,
                "chunk_id": chunk_id,
                "page": page,
                "section": section,
                "breadcrumb": breadcrumb,
                "context": context_snippet,
            })
        return topics

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

            n_items = min(batch_size, target - len(items))

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

            system_instruction = (
                f"ROLE: Senior instructional designer expert in {request.niche}. "
                f"Writing for profile '{request.recipient_profile}'. "
                "OUTPUT FORMAT: Return strictly a valid JSON array of objects."
            )

            raw = None
            if tracer:
                tracer.record_llm_call("generar")

            # Cascade: attempt each LLM provider in order until one succeeds
            for llm in self._llm_cascade:
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
        verified = []
        default_passage = passages[0] if passages else {}
        default_chunk_id = default_passage.get("id", "chunk-rag-001")
        default_section = default_passage.get("title") or default_passage.get("metadata", {}).get("section_title")
        default_breadcrumb = default_passage.get("breadcrumb") or default_passage.get("metadata", {}).get("breadcrumb")
        raw_default_page = default_passage.get("metadata", {}).get("page_number")
        default_page = raw_default_page if isinstance(raw_default_page, int) and raw_default_page > 0 else None

        for item in items:
            sources = item.get("fuentes") or item.get("sources")
            if not sources or not isinstance(sources, list):
                fallback_source: Dict[str, Any] = {
                    "chunk_id": default_chunk_id,
                    "extracto": self._get_item_text(item)[:100],
                    "similitud_score": 0.95,
                }
                if default_section:
                    fallback_source["seccion"] = default_section
                if default_breadcrumb:
                    fallback_source["breadcrumb"] = default_breadcrumb
                if default_page is not None:
                    fallback_source["pagina"] = default_page
                item["fuentes"] = [fallback_source]
            else:
                # Normalise existing sources: strip page when it is a sentinel (0 or None)
                for src in sources:
                    if isinstance(src, dict):
                        p = src.get("pagina")
                        if not isinstance(p, int) or p <= 0:
                            src.pop("pagina", None)
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
    ) -> List[Dict[str, Any]]:
        extra = []
        max_idx = len(existing_items)
        for i in range(needed):
            topic = topics[i % len(topics)] if topics else {
                "topic": doc_title, "chunk_id": "chunk-001", "page": 1, "context": doc_title
            }
            extra.append(
                self._generate_fallback_item(
                    request=request, doc_title=doc_title, topic=topic, item_idx=max_idx + i + 1
                )
            )
        return extra

    # ---------------------------------------------------------------------------
    # STAGE F: CRITIC EVALUATION
    # ---------------------------------------------------------------------------
    def _evaluate_quality_with_critic(
        self, request: AdaptationRequest, generated_items: List[Dict[str, Any]], passages: List[Dict[str, Any]], fallback_score: float
    ) -> QualityEvaluation:
        if not self.groq_client.is_available:
            return QualityEvaluation(
                source_grounding_score=fallback_score,
                pedagogical_clarity="High",
                observations="Batch agentic generation. (Heuristic evaluation; Groq not available.)"
            )
            
        system_instruction = "You are a pedagogical critic evaluating generated educational content."
        context_str = "\n".join([str(p.get("content", p.get("text", "")))[:300] for p in passages[:3]])
        items_str = json.dumps([self._get_item_text(i) for i in generated_items[:3]], ensure_ascii=False)
        
        prompt = f"""
Evaluate the following educational content generated for the profile '{request.recipient_profile}'.
Source Context excerpts:
{context_str}

Generated Items (sample):
{items_str}

Return a valid JSON with:
- "source_grounding_score": float between 0.0 and 1.0 (how well it reflects the source).
- "pedagogical_clarity": string ("High", "Medium", "Low").
- "observations": A short sentence justifying the evaluation.
"""
        try:
            raw = self.groq_client.generate(prompt=prompt, system_instruction=system_instruction, json_output=True)
            text = raw.strip() if raw else "{}"
            text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            
            return QualityEvaluation(
                source_grounding_score=float(data.get("source_grounding_score", fallback_score)),
                pedagogical_clarity=data.get("pedagogical_clarity", "High"),
                observations=data.get("observations", "Evaluated by Groq critic agent.")
            )
        except Exception as e:
            logger.warning(f"Critic agent failed: {e}")
            return QualityEvaluation(
                source_grounding_score=fallback_score,
                pedagogical_clarity="High",
                observations="Heuristic fallback evaluation due to critic agent failure."
            )

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
        self, request: AdaptationRequest, passages_count: int
    ) -> Tuple[int, int, Optional[str]]:
        fmt_key = (request.output_format or "flashcards").lower()
        lvl_key = (request.quantity_level or "estandar").lower()

        base_target = QUANTITY_TABLE.get(fmt_key, {}).get(lvl_key, 20)
        target_quantity = request.target_quantity if request.target_quantity is not None else (
            base_target if request.quantity_level else (request.quantity or base_target)
        )

        cap_factor = FORMAT_CAPACITY_FACTOR.get(fmt_key, 4)
        max_capacity = max(5, max(1, passages_count) * cap_factor)
        effective_target = min(target_quantity, max_capacity)

        warning = None
        if effective_target < target_quantity:
            warning = get_capacity_warning_es(effective_target, target_quantity)
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
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return None

    def _generate_fallback_batch(
        self, request: AdaptationRequest, doc_title: str, topic: Dict[str, Any], n_items: int, offset: int
    ) -> List[Dict[str, Any]]:
        return [
            self._generate_fallback_item(request, doc_title, topic, offset + i + 1)
            for i in range(n_items)
        ]

    def _generate_fallback_item(
        self, request: AdaptationRequest, doc_title: str, topic: Dict[str, Any], item_idx: int
    ) -> Dict[str, Any]:
        fmt = request.output_format.lower()
        topic_name = topic["topic"]
        main_concept = topic.get("concept", topic_name.split("(")[0].strip())
        context = topic.get("context", "")

        sentences = [s.strip() for s in re.split(r"[.!?]", context) if len(s.strip()) > 15]
        target_sentence = sentences[item_idx % len(sentences)] if sentences else f"Key definition of {main_concept}."

        fuente: Dict[str, Any] = {
            "chunk_id": topic.get("chunk_id", "chunk-001"),
            "extracto": target_sentence[:100],
            "similitud_score": 0.92,
        }
        if topic.get("section"):
            fuente["seccion"] = topic["section"]
        if topic.get("breadcrumb"):
            fuente["breadcrumb"] = topic["breadcrumb"]
        page_val = topic.get("page")
        if isinstance(page_val, int) and page_val > 0:
            fuente["pagina"] = page_val

        if "flashcard" in fmt:
            return {
                "frente": f"What is the purpose and application of '{main_concept}' in {topic_name}?",
                "dorso": f"{target_sentence} Optimizes performance and robustness in {request.niche}.",
                "pista_didactica": f"Hint: Assess the operational impact of {main_concept}.",
                "fuentes": [fuente],
            }
        elif "quiz" in fmt:
            return {
                "pregunta": f"Regarding {main_concept} in {topic_name}, which of the following statements is correct?",
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
            return {
                "paso": item_idx,
                "titulo": f"Step {item_idx}: Configuring {main_concept}",
                "instruccion": f"Implement {main_concept} following the {topic_name} guidelines: {target_sentence}",
                "ejemplo": f"// Configuration example for {main_concept}\napply_rule('{main_concept}')",
                "fuentes": [fuente],
            }
        else:
            return {
                "punto_clave": f"{main_concept}: {target_sentence}",
                "impacto_negocio": f"Ensures operational efficiency and strategic value in {request.niche}.",
                "fuentes": [fuente],
            }

    def _format_adapted_content(
        self, request: AdaptationRequest, doc_title: str, items: List[Dict[str, Any]], effective_count: int
    ) -> AdaptedContent:
        fmt = request.output_format.lower()
        intro = (
            f"Adapted version of '{doc_title}' structured into {effective_count} elements "
            f"for {request.recipient_profile} in the {request.niche} sector."
        )

        title_template = TITLE_TEMPLATES_ES.get(
            fmt, "Educational Content ({count} Items): {doc_title}"
        )
        final_title = title_template.format(count=effective_count, doc_title=doc_title)

        if "quiz" in fmt:
            quizzes = [
                QuizItem(
                    question=it.get("pregunta", f"Pregunta #{i+1}"),
                    options=it.get("opciones", ["A", "B", "C", "D"]),
                    correct_answer=it.get("respuesta_correcta", "A"),
                    didactic_justification=it.get("justificacion_didactica") or it.get("justificacion") or "Core technical foundation.",
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
                    "encabezado": f"Step {it.get('paso', i+1)}: {it.get('titulo', 'Module ' + str(i+1))}",
                    "contenido": f"{it.get('instruccion', '')}\n\n{it.get('ejemplo', '')}",
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
                f"{i+1}. {it.get('punto_clave', 'Point ' + str(i+1))}: {it.get('impacto_negocio', '')}"
                for i, it in enumerate(items)
            ]
            return AdaptedContent(
                title=final_title,
                contextualized_introduction=intro,
                executive_summary=f"EXECUTIVE SUMMARY ({effective_count} POINTS):\n\n" + "\n".join(summary_bullets),
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
