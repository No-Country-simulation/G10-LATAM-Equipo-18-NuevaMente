"""
langgraph_orchestrator.py

Purpose:
    Multi-agent graph-based orchestration for educational content adaptation
    using LangGraph (StateGraph).
    Formalizes the pedagogical pipeline into specialized, decoupled nodes:
      - Planner Node: document coverage and topic structuring.
      - Writer Node: multi-model cascading generation by topic batches.
      - Deduplicator Node: fuzzy string duplicate detection and pruning.
      - Grounding Verifier Node: source citation and passage verification.
      - Critic Node: educational quality audit and factual consistency scoring.
      - Refiner Node: conditional self-correction and item completion loop.
      - Formatter Node: Pydantic response assembly, artifact storage, and PDF export.

Output:
    AdaptationResponse schema strictly compatible with frontend and API contracts.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.schemas.adaptation import (
    AdaptationRequest,
    AdaptationResponse,
    OCIStorageResult,
    QualityEvaluation,
    ResponseMetadata,
)
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.coverage_planner import CoveragePlan, CoveragePlanner
from app.services.pdf_export_service import PDFExportService

logger = logging.getLogger("LangGraphOrchestrator")


class AgentState(TypedDict, total=False):
    """Shared state dictionary representing the workflow context across graph nodes."""
    # Inputs
    request: AdaptationRequest
    doc_title: str
    target_language: str
    top_passages: List[Dict[str, Any]]
    all_parent_chunks: List[Dict[str, Any]]
    key_concepts: List[str]
    prerequisites: List[str]
    document_id: Optional[str]
    prompt_hash: str
    tracer: Optional[Any]

    # Planning
    coverage_plan: Optional[CoveragePlan]
    target_quantity: int
    effective_target: int
    capacity_warning: Optional[str]
    topics: List[Dict[str, Any]]

    # Generation & Filtering
    raw_items: List[Dict[str, Any]]
    dedup_items: List[Dict[str, Any]]
    verified_items: List[Dict[str, Any]]

    # Critic & Quality Audit
    evaluation: Optional[QualityEvaluation]
    audited_items: List[Dict[str, Any]]
    preliminary_score: float

    # Refinement / Iteration loop
    revision_count: int
    max_revisions: int

    # Graph Trajectory & Final Result
    nodes_executed: List[str]
    final_items: List[Dict[str, Any]]
    final_response: Optional[AdaptationResponse]


class LangGraphOrchestrator:
    """Orchestrates the multi-agent adaptation workflow using a compiled LangGraph StateGraph."""

    def __init__(self, base_orchestrator: Optional[AgentOrchestrator] = None):
        self._orchestrator = base_orchestrator or AgentOrchestrator()
        self._response_cache: Dict[str, AdaptationResponse] = {}
        self.graph = self._build_graph()

    def _build_graph(self):
        """Builds and compiles the StateGraph workflow."""
        workflow = StateGraph(AgentState)

        # 1. Register graph nodes
        workflow.add_node("planner", self._node_planner)
        workflow.add_node("writer", self._node_writer)
        workflow.add_node("deduplicator", self._node_deduplicator)
        workflow.add_node("grounding_verifier", self._node_grounding_verifier)
        workflow.add_node("critic", self._node_critic)
        workflow.add_node("refiner", self._node_refiner)
        workflow.add_node("formatter", self._node_formatter)

        # 2. Define standard linear transitions
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "writer")
        workflow.add_edge("writer", "deduplicator")
        workflow.add_edge("deduplicator", "grounding_verifier")
        workflow.add_edge("grounding_verifier", "critic")

        # 3. Add conditional router from Critic
        workflow.add_conditional_edges(
            "critic",
            self._should_refine_or_complete,
            {
                "refiner": "refiner",
                "formatter": "formatter",
            },
        )

        # 4. Refiner leads to formatter (or back to review)
        workflow.add_edge("refiner", "formatter")
        workflow.add_edge("formatter", END)

        compiled_graph = workflow.compile()
        logger.info("LangGraph workflow compiled successfully with 7 agentic nodes.")
        return compiled_graph

    # ---------------------------------------------------------------------------
    # NODE 1: PLANNER
    # ---------------------------------------------------------------------------
    def _node_planner(self, state: AgentState) -> Dict[str, Any]:
        """Analyzes content coverage and derives structured pedagogical topics."""
        logger.info("📋 [LangGraph Node: Planner] Planificando cobertura y tópicos pedagógicos...")
        request = state["request"]
        doc_title = state["doc_title"]
        target_language = state["target_language"]
        top_passages = state.get("top_passages", [])
        all_parent_chunks = state.get("all_parent_chunks") or top_passages
        key_concepts = state.get("key_concepts", [])
        tracer = state.get("tracer")

        if tracer:
            tracer.start_stage("planificador")

        chunks_for_planning = all_parent_chunks or top_passages
        fmt_key = (request.output_format or "flashcards").lower()
        coverage_plan = CoveragePlanner().plan(
            parent_chunks=chunks_for_planning,
            output_format=fmt_key,
            requested_items=request.target_quantity or request.quantity or 20,
            language=target_language,
        )

        target_quantity, effective_target, capacity_warning = self._orchestrator._calculate_target_quantity(
            request=request,
            coverage_plan=coverage_plan,
            language=target_language,
        )

        topics = self._orchestrator._stage_planner(
            doc_title=doc_title,
            key_concepts=key_concepts,
            coverage_plan=coverage_plan,
            target=effective_target,
            target_language=target_language,
        )

        if tracer:
            tracer.end_stage("planificador")
            tracer.record_llm_call("planificar")

        nodes = state.get("nodes_executed", []) + ["planner"]
        return {
            "coverage_plan": coverage_plan,
            "target_quantity": target_quantity,
            "effective_target": effective_target,
            "capacity_warning": capacity_warning,
            "topics": topics,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # NODE 2: WRITER (BATCH GENERATION)
    # ---------------------------------------------------------------------------
    def _node_writer(self, state: AgentState) -> Dict[str, Any]:
        """Generates educational items using multi-model fallback cascade in batches."""
        logger.info("✍️ [LangGraph Node: Writer] Generando borradores por lotes...")
        request = state["request"]
        doc_title = state["doc_title"]
        topics = state.get("topics", [])
        top_passages = state.get("top_passages", [])
        effective_target = state.get("effective_target", 20)
        target_language = state["target_language"]
        tracer = state.get("tracer")

        if tracer:
            tracer.start_stage("generacion_lotes")

        raw_items = self._orchestrator._stage_batch_generators(
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

        nodes = state.get("nodes_executed", []) + ["writer"]
        return {
            "raw_items": raw_items,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # NODE 3: DEDUPLICATOR
    # ---------------------------------------------------------------------------
    def _node_deduplicator(self, state: AgentState) -> Dict[str, Any]:
        """Removes duplicate and near-duplicate educational items."""
        logger.info("🧹 [LangGraph Node: Deduplicator] Limpiando ítems duplicados...")
        raw_items = state.get("raw_items", [])
        tracer = state.get("tracer")

        if tracer:
            tracer.start_stage("deduplicacion")

        dedup_items = self._orchestrator._stage_deduplicate(raw_items)

        if tracer:
            tracer.end_stage("deduplicacion")

        nodes = state.get("nodes_executed", []) + ["deduplicator"]
        return {
            "dedup_items": dedup_items,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # NODE 4: GROUNDING VERIFIER
    # ---------------------------------------------------------------------------
    def _node_grounding_verifier(self, state: AgentState) -> Dict[str, Any]:
        """Validates that each item is supported by retrieved passages and assigns citations."""
        logger.info("🔍 [LangGraph Node: Grounding Verifier] Verificando citas y anclaje RAG...")
        dedup_items = state.get("dedup_items", [])
        top_passages = state.get("top_passages", [])
        all_parent_chunks = state.get("all_parent_chunks")
        tracer = state.get("tracer")

        if tracer:
            tracer.start_stage("verificacion_anclaje")

        verified_items = self._orchestrator._stage_verify_grounding(
            dedup_items,
            top_passages,
            all_chunks=all_parent_chunks,
        )

        if tracer:
            tracer.end_stage("verificacion_anclaje")

        nodes = state.get("nodes_executed", []) + ["grounding_verifier"]
        return {
            "verified_items": verified_items,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # NODE 5: CRITIC / AUDITOR
    # ---------------------------------------------------------------------------
    def _node_critic(self, state: AgentState) -> Dict[str, Any]:
        """Audits pedagogical clarity and factual precision according to user profile."""
        logger.info("🧐 [LangGraph Node: Critic] Auditando calidad pedagógica y fidelidad...")
        request = state["request"]
        verified_items = state.get("verified_items", [])
        top_passages = state.get("top_passages", [])
        all_parent_chunks = state.get("all_parent_chunks")

        grounded_count = sum(1 for it in verified_items if it.get("grounded", False))
        preliminary_score = round(min(1.0, grounded_count / max(1, len(verified_items))), 2)

        evaluation, audited_items = self._orchestrator._evaluate_quality_with_critic(
            request=request,
            generated_items=verified_items,
            passages=top_passages,
            all_chunks=all_parent_chunks,
            fallback_score=preliminary_score,
        )

        nodes = state.get("nodes_executed", []) + ["critic"]
        return {
            "evaluation": evaluation,
            "audited_items": audited_items,
            "preliminary_score": preliminary_score,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # CONDITIONAL EDGE: SHOULD REFINE OR COMPLETE
    # ---------------------------------------------------------------------------
    def _should_refine_or_complete(self, state: AgentState) -> str:
        """Determines whether to trigger self-correction/completion or proceed to formatting."""
        audited_items = state.get("audited_items", [])
        effective_target = state.get("effective_target", 0)
        coverage_plan = state.get("coverage_plan")
        revision_count = state.get("revision_count", 0)
        max_revisions = state.get("max_revisions", settings.LANGGRAPH_MAX_REVISIONS)

        total_capacity = getattr(coverage_plan, "total_capacity", len(audited_items))

        # Check if items were dropped and document capacity permits generating more
        if len(audited_items) < effective_target and total_capacity > len(audited_items) and revision_count < max_revisions:
            logger.info(
                "LangGraph Conditional Router: Se requieren items complementarios "
                "(actual: %d, objetivo: %d, revisión: %d/%d). Derivando a 'refiner'.",
                len(audited_items),
                effective_target,
                revision_count,
                max_revisions,
            )
            return "refiner"

        logger.info(
            "LangGraph Conditional Router: Calidad aprobada (actual: %d, objetivo: %d). "
            "Derivando a 'formatter'.",
            len(audited_items),
            effective_target,
        )
        return "formatter"

    # ---------------------------------------------------------------------------
    # NODE 6: REFINER / COMPLETION
    # ---------------------------------------------------------------------------
    def _node_refiner(self, state: AgentState) -> Dict[str, Any]:
        """Self-correction loop: generates targeted items to fill gaps detected by the Critic."""
        logger.info("🔄 [LangGraph Node: Refiner] Ejecutando auto-corrección y generación complementaria...")
        request = state["request"]
        doc_title = state["doc_title"]
        topics = state.get("topics", [])
        audited_items = list(state.get("audited_items", []))
        effective_target = state.get("effective_target", 20)
        target_language = state["target_language"]
        revision_count = state.get("revision_count", 0)

        needed = effective_target - len(audited_items)
        if needed > 0:
            extra_items = self._orchestrator._stage_completion(
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

        nodes = state.get("nodes_executed", []) + ["refiner"]
        return {
            "audited_items": audited_items,
            "revision_count": revision_count + 1,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # NODE 7: FORMATTER & STORAGE
    # ---------------------------------------------------------------------------
    def _node_formatter(self, state: AgentState) -> Dict[str, Any]:
        """Formats the final educational structure, uploads to OCI, and builds AdaptationResponse."""
        logger.info("📦 [LangGraph Node: Formatter] Serializando respuesta y guardando artefactos...")
        request = state["request"]
        doc_title = state["doc_title"]
        audited_items = state.get("audited_items", [])
        effective_target = state.get("effective_target", 20)
        target_quantity = state.get("target_quantity", 20)
        capacity_warning = state.get("capacity_warning")
        target_language = state["target_language"]
        evaluation = state.get("evaluation")
        key_concepts = state.get("key_concepts", [])
        prerequisites = state.get("prerequisites", [])
        document_id = state.get("document_id")
        tracer = state.get("tracer")
        nodes_executed = state.get("nodes_executed", []) + ["formatter"]
        revision_count = state.get("revision_count", 0)

        if tracer:
            tracer.start_stage("serializacion_respuesta")

        final_items = audited_items[:effective_target]
        items_generated = len(final_items)

        adapted_content = self._orchestrator._format_adapted_content(
            request=request,
            doc_title=doc_title,
            items=final_items,
            effective_count=items_generated,
            target_language=target_language,
        )

        if tracer:
            tracer.end_stage("serializacion_respuesta")

        # Grounding verification score
        verified_citations = sum(
            1 for it in final_items if any(s.get("verificado", False) for s in (it.get("fuentes") or []))
        )
        heuristic_score = round(min(1.0, verified_citations / max(1, items_generated)), 2)
        if evaluation:
            grounding_score = max(heuristic_score, evaluation.source_grounding_score)
            evaluation.source_grounding_score = round(grounding_score, 2)
        else:
            evaluation = QualityEvaluation(
                source_grounding_score=heuristic_score,
                pedagogical_clarity="Alta",
                observations="Validado contra pasajes fuente.",
            )

        # Resolve vector store model if available
        embedding_provider = "gemini"
        embedding_model_name = None
        try:
            from app.services.vector_store_service import get_store
            store = get_store(document_id)
            if store and store.model_name:
                embedding_model_name = store.model_name.split("@")[0].replace("models/", "")
                lower_em = embedding_model_name.lower()
                if "gemini" in lower_em:
                    embedding_provider = "gemini"
                elif "jina" in lower_em:
                    embedding_provider = "jina"
                else:
                    embedding_provider = "local"
        except Exception:
            pass

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
            llm_provider=self._orchestrator.last_provider,
            llm_model=self._orchestrator.last_model,
            models_used=self._orchestrator._format_models_used(),
            critic_provider=self._orchestrator.critic_provider,
            critic_model=self._orchestrator.critic_model,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model_name,
            retrieval_mode="hibrido_rrf_reranker",
            timings=tracer.timings if tracer else {},
            llm_calls=tracer.llm_calls if tracer else {},
            graph_orchestration=True,
            graph_nodes_executed=nodes_executed,
            graph_revision_count=revision_count,
        )

        object_name = (
            f"contenido-{self._orchestrator._slugify(doc_title)[:20]}-"
            f"{self._orchestrator._slugify(request.recipient_profile)[:15]}-{int(time.time())}.json"
        )
        from app.services.storage_queue_service import StorageQueueService
        content_id = f"cnt_{int(time.time() * 1000)}"
        user_id = getattr(request, "user_id", None) or "usr_demo_001"
        version_num = getattr(request, "version", 1) or 1

        response_payload = {
            "status": "exito",
            "content_id": content_id,
            "metadatos": metadata.model_dump(by_alias=True),
            "contenido_adaptado": adapted_content.model_dump(by_alias=True),
            "evaluacion_calidad": evaluation.model_dump(by_alias=True),
        }

        queue_service = StorageQueueService.get_instance()
        job_info = queue_service.enqueue_content_job(
            content_id=content_id,
            user_id=user_id,
            json_data=response_payload,
            version=version_num,
        )
        immediate_ok = queue_service.process_job(job_info["job_id"])
        upload_status_val = "completado" if immediate_ok else "pendiente"

        # Record the generated package in `contenidos`: the library and trash
        # flows read that table, so without this row the content exists in
        # storage but is invisible in the app.
        queue_service.save_content_metadata(
            content_id=content_id,
            user_id=user_id,
            title=doc_title,
            content=json.dumps(adapted_content.model_dump(by_alias=True), ensure_ascii=False),
            recipient_profile=request.recipient_profile,
            output_format=request.output_format,
            niche=getattr(request, "niche", None),
            detail_level=getattr(request, "detail_level", None),
            object_key_json=job_info["objeto_id"],
        )

        storage_result = OCIStorageResult(
            bucket=job_info["bucket"],
            object_id=job_info["objeto_id"],
            upload_status=upload_status_val,
        )

        try:
            pdf_service = PDFExportService()
            output_name = f"scratch/{object_name.replace('.json', '.pdf')}"
            pdf_service.generate_pdf(content=adapted_content, output_path=output_name)
        except Exception as e:
            logger.warning("Error generando PDF en LangGraph Formatter: %s", e)

        final_response = AdaptationResponse(
            status="exito",
            metadata=metadata,
            adapted_content=adapted_content,
            quality_evaluation=evaluation,
            oci_storage=storage_result,
        )

        prompt_hash = state.get("prompt_hash")
        if prompt_hash:
            self._response_cache[prompt_hash] = final_response

        return {
            "final_items": final_items,
            "final_response": final_response,
            "nodes_executed": nodes_executed,
        }

    # ---------------------------------------------------------------------------
    # ENTRY POINT PIPELINE
    # ---------------------------------------------------------------------------
    async def run_pipeline(
        self,
        request: AdaptationRequest,
        top_passages: List[Dict[str, Any]],
        key_concepts: List[str],
        prerequisites: List[str],
        tracer: Optional[Any] = None,
        all_parent_chunks: Optional[List[Dict[str, Any]]] = None,
        document_id: Optional[str] = None,
    ) -> AdaptationResponse:
        """Executes the compiled multi-agent LangGraph pipeline."""
        doc_title = self._orchestrator._clean_document_title(request)
        target_language = request.language or settings.DEFAULT_OUTPUT_LANGUAGE
        prompt_hash = self._orchestrator._compute_request_hash(request, doc_title, target_language)

        force_regenerate = getattr(request, "force_regenerate", False) or getattr(request, "forzar_regenerar", False)
        if not force_regenerate and prompt_hash in self._response_cache:
            cached_resp = self._response_cache[prompt_hash]
            cached_resp.metadata.origin = "cache"
            cached_resp.metadata.prompt_hash = prompt_hash
            if tracer:
                cached_resp.metadata.timings = {"cache": tracer.total_elapsed_ms()}
                cached_resp.metadata.llm_calls = tracer.llm_calls
            return cached_resp

        # Initial graph state
        initial_state: AgentState = {
            "request": request,
            "doc_title": doc_title,
            "target_language": target_language,
            "top_passages": top_passages,
            "all_parent_chunks": all_parent_chunks or top_passages,
            "key_concepts": key_concepts,
            "prerequisites": prerequisites,
            "document_id": document_id,
            "prompt_hash": prompt_hash,
            "tracer": tracer,
            "revision_count": 0,
            "max_revisions": settings.LANGGRAPH_MAX_REVISIONS,
            "nodes_executed": [],
        }

        # Run the LangGraph execution
        logger.info("🚀 Iniciando ejecución del grafo de LangGraph para doc='%s'...", doc_title)
        final_state = await self.graph.ainvoke(initial_state)

        final_response = final_state.get("final_response")
        if not final_response:
            logger.warning("El grafo no produjo final_response directamente; ejecutando formatter de respaldo.")
            formatter_output = self._node_formatter(final_state)
            final_response = formatter_output["final_response"]

        logger.info(
            "🎉 LangGraph completado exitosamente. Nodos ejecutados: %s",
            final_response.metadata.graph_nodes_executed,
        )
        return final_response
