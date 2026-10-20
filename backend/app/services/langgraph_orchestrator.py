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
      - Repair Node: surgical LLM-based rewrite of ungrounded/low-clarity items.
      - Refiner Node: conditional self-correction and item completion loop.
      - Formatter Node: Pydantic response assembly, artifact storage, and PDF export.

Output:
    AdaptationResponse schema strictly compatible with frontend and API contracts.
"""

import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.schemas.adaptation import (
    AdaptationRequest,
    AdaptationResponse,
    OCIStorageResult,
    QualityEvaluation,
    ResponseMetadata,
)
from app.services.pipeline_stages import PipelineStages, _is_spanish
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
    repaired_indices: List[int]

    # Graph Trajectory & Final Result
    nodes_executed: List[str]
    final_items: List[Dict[str, Any]]
    final_response: Optional[AdaptationResponse]


class LangGraphOrchestrator(PipelineStages):
    """Orchestrates the multi-agent adaptation workflow using a compiled LangGraph StateGraph."""

    def __init__(self):
        super().__init__()
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
        workflow.add_node("repair", self._node_repair)
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
                "repair": "repair",
                "refiner": "refiner",
                "formatter": "formatter",
            },
        )

        # 4. Transitions from self-correction nodes to formatter
        workflow.add_edge("repair", "formatter")
        workflow.add_edge("refiner", "formatter")
        workflow.add_edge("formatter", END)

        compiled_graph = workflow.compile()
        logger.info("LangGraph workflow compiled successfully with 8 agentic nodes.")
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

        target_quantity, effective_target, capacity_warning = self._calculate_target_quantity(
            request=request,
            coverage_plan=coverage_plan,
            language=target_language,
        )

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

        dedup_items = self._stage_deduplicate(raw_items)

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

        verified_items = self._stage_verify_grounding(
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
        target_language = state.get("target_language", "Spanish")

        # Ensure all incoming items have stable _gid
        for i, it in enumerate(verified_items):
            if "_gid" not in it:
                it["_gid"] = f"ground_{i}"

        grounded_count = sum(1 for it in verified_items if it.get("grounded", False))
        preliminary_score = round(min(1.0, grounded_count / max(1, len(verified_items))), 2)

        evaluation, audited_items = self._evaluate_quality_with_critic(
            request=request,
            generated_items=verified_items,
            passages=top_passages,
            all_chunks=all_parent_chunks,
            fallback_score=preliminary_score,
            target_language=target_language,
        )

        nodes = state.get("nodes_executed", []) + ["critic"]
        return {
            "evaluation": evaluation,
            "audited_items": audited_items,
            "preliminary_score": preliminary_score,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # CONDITIONAL EDGE: SHOULD REPAIR, REFINE, OR COMPLETE
    # ---------------------------------------------------------------------------
    def _should_refine_or_complete(self, state: AgentState) -> str:
        """
        Routing decision after the Critic node.

        Priority:
          1. 'repair'  — if any item is ungrounded or low-clarity and has not
                         already been repaired, and revision budget allows it.
          2. 'refiner' — if item count is below the effective target and the
                         document has remaining capacity.
          3. 'formatter' — otherwise (quality approved or budget exhausted).
        """
        audited_items = state.get("audited_items", [])
        effective_target = state.get("effective_target", 0)
        coverage_plan = state.get("coverage_plan")
        revision_count = state.get("revision_count", 0)
        max_revisions = state.get("max_revisions", settings.LANGGRAPH_MAX_REVISIONS)
        repaired_indices = set(state.get("repaired_indices", []))

        total_capacity = getattr(coverage_plan, "total_capacity", len(audited_items))

        # Identify items that need repair and have not been repaired yet.
        # An item needs repair when it has no verified source or its critic
        # per_item record reports low clarity. Cross-reference by _gid or index.
        evaluation = state.get("evaluation")
        per_item_by_gid: dict = {}
        if evaluation and hasattr(evaluation, "per_item") and evaluation.per_item:
            for rec in evaluation.per_item:
                if isinstance(rec, dict):
                    gid = rec.get("_gid") or f"ground_{rec.get('index', 0)}"
                    per_item_by_gid[gid] = rec

        repair_candidates = []
        for idx, item in enumerate(audited_items):
            if idx in repaired_indices:
                continue
            # Ungrounded: no source is verified
            ungrounded = not any(s.get("verificado", False) for s in (item.get("fuentes") or []))
            # Low clarity from critic per-item record matching by _gid
            low_clarity = False
            item_gid = item.get("_gid", f"ground_{idx}")
            if item_gid in per_item_by_gid:
                clarity = per_item_by_gid[item_gid].get("claridad", "")
                low_clarity = clarity in ("Baja", "Low")
            if ungrounded or low_clarity:
                repair_candidates.append(idx)

        if repair_candidates and revision_count < max_revisions:
            logger.info(
                "LangGraph Conditional Router: %d item(s) requieren reparación quirúrgica "
                "(índices: %s, revisión: %d/%d). Derivando a 'repair'.",
                len(repair_candidates),
                repair_candidates,
                revision_count,
                max_revisions,
            )
            return "repair"

        # Fallback to refiner if quantity is still below target
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
    # NODE 6: REPAIR — SURGICAL LLM REWRITE OF FAILED ITEMS
    # ---------------------------------------------------------------------------
    def _node_repair(self, state: AgentState) -> Dict[str, Any]:
        """
        Identifies ungrounded or low-clarity items not yet repaired, sends them
        to the LLM repair stage in a single batch call, re-runs grounding
        verification on the results, and writes the updated items back into
        `audited_items`. Each repaired item's index is recorded in
        `repaired_indices` so the anti-loop guarantee holds: an item is never
        sent to repair more than once.
        """
        logger.info("🔧 [LangGraph Node: Repair] Iniciando reparación quirúrgica de ítems no anclados...")
        audited_items = list(state.get("audited_items", []))
        repaired_indices = list(state.get("repaired_indices", []))
        repaired_set = set(repaired_indices)
        revision_count = state.get("revision_count", 0)
        top_passages = state.get("top_passages", [])
        all_parent_chunks = state.get("all_parent_chunks")
        target_language = state.get("target_language", "Spanish")
        request = state["request"]

        # Rebuild the per-item critic map by _gid for clarity information
        evaluation = state.get("evaluation")
        per_item_by_gid: dict = {}
        if evaluation and hasattr(evaluation, "per_item") and evaluation.per_item:
            for rec in evaluation.per_item:
                if isinstance(rec, dict):
                    gid = rec.get("_gid") or f"ground_{rec.get('index', 0)}"
                    per_item_by_gid[gid] = rec

        # Collect (index, item, issues) tuples for items that need repair
        items_to_repair = []
        for idx, item in enumerate(audited_items):
            if idx in repaired_set:
                continue
            item_gid = item.get("_gid", f"ground_{idx}")
            ungrounded = not any(s.get("verificado", False) for s in (item.get("fuentes") or []))
            low_clarity = False
            issues: List[str] = []
            if item_gid in per_item_by_gid:
                clarity = per_item_by_gid[item_gid].get("claridad", "")
                low_clarity = clarity in ("Baja", "Low")
                issues = per_item_by_gid[item_gid].get("issues", [])
            if ungrounded:
                issues = ["Ungrounded: no cited source was verified."] + issues
            if ungrounded or low_clarity:
                items_to_repair.append((idx, item, issues))

        if not items_to_repair:
            logger.info("[Repair] No items require surgical repair; passing through.")
            nodes = state.get("nodes_executed", []) + ["repair"]
            return {"nodes_executed": nodes, "revision_count": revision_count + 1}

        logger.info("[Repair] Reparando %d ítem(s): índices %s", len(items_to_repair), [i for i, _, _ in items_to_repair])

        # Surgical LLM batch repair
        repair_results = self._stage_repair_items(
            request=request,
            items_to_repair=items_to_repair,
            passages=top_passages,
            all_chunks=all_parent_chunks,
            target_language=target_language,
        )

        # Re-verify grounding on repaired items before writing them back
        for orig_idx, repaired_item in repair_results:
            # Preserve original item's _gid
            orig_gid = audited_items[orig_idx].get("_gid", f"ground_{orig_idx}")
            repaired_item["_gid"] = orig_gid
            verified_single = self._stage_verify_grounding(
                [repaired_item],
                top_passages,
                all_chunks=all_parent_chunks,
            )
            item_to_store = verified_single[0] if verified_single else repaired_item
            item_to_store["_gid"] = orig_gid
            audited_items[orig_idx] = item_to_store
            repaired_indices.append(orig_idx)

        # Check if any repaired item is still garbage/ungrounded; if so, discard and prepare for replacement
        filtered_items = []
        for idx, it in enumerate(audited_items):
            gid = it.get("_gid", f"ground_{idx}")
            crit_rec = per_item_by_gid.get(gid)
            is_garbage = self._is_garbage_item(it, crit_rec)
            is_unverified = not any(s.get("verificado", False) for s in (it.get("fuentes") or []))
            if idx in repaired_set or idx in [r[0] for r in repair_results]:
                # If it was repaired but still fails, discard it
                if is_garbage or is_unverified:
                    logger.info("[Repair] Descartando ítem inutilizable post-reparación (índice: %d, gid: %s)", idx, gid)
                    continue
            filtered_items.append(it)

        # If items were discarded, fill deficit with newly refined items from unused topics
        deficit = effective_target - len(filtered_items)
        if deficit > 0 and revision_count < max_revisions:
            logger.info("[Repair] Reponiendo %d ítem(s) descartados vía refiner...", deficit)
            extra_replacements = self._stage_completion(
                request=request,
                doc_title=doc_title,
                topics=topics,
                needed=deficit,
                existing_items=filtered_items,
                target_language=target_language,
            )
            verified_replacements = self._stage_verify_grounding(
                extra_replacements,
                top_passages,
                all_chunks=all_parent_chunks,
            )
            for idx_rep, rep_item in enumerate(verified_replacements):
                # Only publish replacement if verified
                rep_verified = any(s.get("verificado", False) for s in (rep_item.get("fuentes") or []))
                if rep_verified and not self._is_garbage_item(rep_item):
                    if "_gid" not in rep_item:
                        rep_item["_gid"] = f"replace_{len(filtered_items)}_{idx_rep}"
                    filtered_items.append(rep_item)

        audited_items = filtered_items
        nodes = state.get("nodes_executed", []) + ["repair"]
        logger.info("[Repair] Reparación y descarte completados. Ítems vigentes: %d", len(audited_items))
        return {
            "audited_items": audited_items,
            "repaired_indices": repaired_indices,
            "revision_count": revision_count + 1,
            "nodes_executed": nodes,
        }

    # ---------------------------------------------------------------------------
    # NODE 7: REFINER / COMPLETION
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
            extra_items = self._stage_completion(
                request=request,
                doc_title=doc_title,
                topics=topics,
                needed=needed,
                existing_items=audited_items,
                target_language=target_language,
            )
            # Refined items must pass through grounding verification
            top_passages = state.get("top_passages", [])
            all_parent_chunks = state.get("all_parent_chunks")
            verified_extras = self._stage_verify_grounding(
                extra_items,
                top_passages,
                all_chunks=all_parent_chunks,
            )
            for idx_extra, extra in enumerate(verified_extras):
                is_ok = any(s.get("verificado", False) for s in (extra.get("fuentes") or [])) and not self._is_garbage_item(extra)
                if is_ok:
                    if "_gid" not in extra:
                        extra["_gid"] = f"refine_{len(audited_items)}_{idx_extra}"
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

        # Exclude any garbage items from publishing entirely
        evaluation_map: dict = {}
        if evaluation and hasattr(evaluation, "per_item") and evaluation.per_item:
            for rec in evaluation.per_item:
                if isinstance(rec, dict):
                    gid = rec.get("_gid") or f"ground_{rec.get('index', 0)}"
                    evaluation_map[gid] = rec

        clean_audited_items = [
            it for it in audited_items
            if not self._is_garbage_item(it, evaluation_map.get(it.get("_gid", "")))
        ]

        final_items = clean_audited_items[:effective_target]
        items_generated = len(final_items)

        adapted_content = self._format_adapted_content(
            request=request,
            doc_title=doc_title,
            items=final_items,
            effective_count=items_generated,
            target_language=target_language,
        )

        if tracer:
            tracer.end_stage("serializacion_respuesta")

        # Grounding verification score:
        # Respect combined criterion: both lexical heuristic (verificado_lexico) AND
        # critic reviewer verdict (verificado_revisor). Never overwrite critic verdict.
        is_spanish = _is_spanish(target_language)
        has_per_item = bool(evaluation and hasattr(evaluation, "per_item") and evaluation.per_item)

        if has_per_item:
            existing_by_gid = {
                rec.get("_gid", f"ground_{rec.get('index')}"): rec
                for rec in evaluation.per_item
                if isinstance(rec, dict)
            }
            final_per_item = []
            verified_count = 0
            for idx, it in enumerate(final_items):
                gid = it.get("_gid", f"ground_{idx}")
                existing_rec = existing_by_gid.get(gid)

                verificado_lexico = bool(any(s.get("verificado", False) for s in (it.get("fuentes") or [])))
                # If critic audited this item, retain its verificado_revisor. Otherwise fallback to True.
                if existing_rec and "verificado_revisor" in existing_rec:
                    verificado_revisor = bool(existing_rec["verificado_revisor"])
                elif existing_rec and "origen_verificado" in existing_rec:
                    verificado_revisor = bool(existing_rec.get("verificado_revisor", existing_rec["origen_verificado"]))
                else:
                    verificado_revisor = True

                origen_verificado = bool(verificado_lexico and verificado_revisor)
                if origen_verificado:
                    verified_count += 1

                claridad = (existing_rec.get("claridad") if existing_rec else None) or evaluation.pedagogical_clarity or ("Alta" if is_spanish else "High")
                issues = (existing_rec.get("issues") if existing_rec else None)
                if issues is None:
                    issues = [] if origen_verificado else ["Sin verificación de cita."]

                final_per_item.append({
                    "index": idx,
                    "_gid": gid,
                    "verificado_lexico": verificado_lexico,
                    "verificado_revisor": verificado_revisor,
                    "origen_verificado": origen_verificado,
                    "claridad": claridad,
                    "issues": issues,
                    "es_fallback": bool(it.get("es_fallback", False)),
                })

            combined_ratio = round(min(1.0, verified_count / max(1, items_generated)), 2)
            # Conservative principle: floor (min) between combined ratio and critic overall score
            evaluation.source_grounding_score = round(min(combined_ratio, evaluation.source_grounding_score), 2)
            evaluation.per_item = final_per_item

            count_note = (
                f"{verified_count} de {items_generated} elementos verificados."
                if is_spanish
                else f"{verified_count} of {items_generated} items verified."
            )
            base_obs = (evaluation.observations or "").strip()
            if count_note not in base_obs:
                evaluation.observations = f"{count_note} {base_obs}".strip()
        else:
            verified_count = sum(
                1 for it in final_items if any(s.get("verificado", False) for s in (it.get("fuentes") or []))
            )
            heuristic_score = round(min(1.0, verified_count / max(1, items_generated)), 2)
            per_item_records = [
                {
                    "index": idx,
                    "_gid": it.get("_gid", f"ground_{idx}"),
                    "verificado_lexico": any(s.get("verificado", False) for s in (it.get("fuentes") or [])),
                    "verificado_revisor": True,
                    "origen_verificado": any(s.get("verificado", False) for s in (it.get("fuentes") or [])),
                    "claridad": "Alta" if is_spanish else "High",
                    "issues": [] if any(s.get("verificado", False) for s in (it.get("fuentes") or [])) else ["Sin verificación de cita."],
                    "es_fallback": bool(it.get("es_fallback", False)),
                }
                for idx, it in enumerate(final_items)
            ]
            count_note = (
                f"{verified_count} de {items_generated} elementos verificados."
                if is_spanish
                else f"{verified_count} of {items_generated} items verified."
            )
            obs_suffix = "Validado contra pasajes fuente." if is_spanish else "Validated against source passages."
            if evaluation:
                grounding_score = min(heuristic_score, evaluation.source_grounding_score)
                evaluation.source_grounding_score = round(grounding_score, 2)
                evaluation.per_item = per_item_records
                base_obs = (evaluation.observations or "").strip()
                if count_note not in base_obs:
                    evaluation.observations = f"{count_note} {base_obs}".strip()
            else:
                evaluation = QualityEvaluation(
                    source_grounding_score=heuristic_score,
                    pedagogical_clarity="Alta" if is_spanish else "High",
                    observations=f"{count_note} {obs_suffix}",
                    per_item=per_item_records,
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

        # Collect which item indices were surgically repaired during this run
        repaired_items_list = state.get("repaired_indices", [])

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
            llm_model=self.last_model,
            models_used=self._format_models_used(),
            models_used_detail=self._format_models_detail(),
            critic_provider=self.critic_provider,
            critic_model=self.critic_model,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model_name,
            retrieval_mode="hibrido_rrf_reranker",
            timings=tracer.timings if tracer else {},
            llm_calls=tracer.llm_calls if tracer else {},
            graph_orchestration=True,
            graph_nodes_executed=nodes_executed,
            graph_revision_count=revision_count,
            repaired_items=repaired_items_list,
        )

        object_name = (
            f"contenido-{self._slugify(doc_title)[:20]}-"
            f"{self._slugify(request.recipient_profile)[:15]}-{int(time.time())}.json"
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
            output_format=request.output_format,
            document_title=doc_title,
            recipient_profile=request.recipient_profile,
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
            # Full response (metadata + quality evaluation) so the Library can
            # show the real RAG anchoring score instead of a hardcoded one.
            response_json=json.dumps(response_payload, ensure_ascii=False),
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

        # Initial graph state
        initial_state = self._build_initial_state(
            request=request,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites,
            tracer=tracer,
            all_parent_chunks=all_parent_chunks,
            document_id=document_id,
            doc_title=doc_title,
            target_language=target_language,
            prompt_hash=prompt_hash,
        )

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

    def _build_initial_state(
        self,
        request: AdaptationRequest,
        top_passages: List[Dict[str, Any]],
        key_concepts: List[str],
        prerequisites: List[str],
        tracer: Optional[Any],
        all_parent_chunks: Optional[List[Dict[str, Any]]],
        document_id: Optional[str],
        doc_title: str,
        target_language: str,
        prompt_hash: str,
    ) -> AgentState:
        """Builds the initial AgentState shared by the sync and streaming entry points."""
        return {
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
            "repaired_indices": [],
            "nodes_executed": [],
        }

    async def iter_pipeline(
        self,
        request: AdaptationRequest,
        top_passages: List[Dict[str, Any]],
        key_concepts: Optional[List[str]] = None,
        prerequisites: Optional[List[str]] = None,
        tracer: Optional[Any] = None,
        all_parent_chunks: Optional[List[Dict[str, Any]]] = None,
        document_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Streams one progress event per executed graph node.

        Yields `{"stage": <node_name>}` after each node finishes and a final
        `{"stage": "done", "response": <AdaptationResponse>}`. The node names
        match the graph keys (planner, writer, deduplicator,
        grounding_verifier, critic, refiner, formatter), so callers can map
        them to their own step labels.
        """
        key_concepts = key_concepts or []
        prerequisites = prerequisites or []
        doc_title = self._clean_document_title(request)
        target_language = request.language or settings.DEFAULT_OUTPUT_LANGUAGE
        prompt_hash = self._compute_request_hash(request, doc_title, target_language)

        force_regenerate = getattr(request, "force_regenerate", False) or getattr(request, "forzar_regenerar", False)
        if not force_regenerate and prompt_hash in self._response_cache:
            cached_resp = self._response_cache[prompt_hash]
            cached_resp.metadata.origin = "cache"
            cached_resp.metadata.prompt_hash = prompt_hash
            yield {"stage": "done", "response": cached_resp}
            return

        initial_state = self._build_initial_state(
            request=request,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites,
            tracer=tracer,
            all_parent_chunks=all_parent_chunks,
            document_id=document_id,
            doc_title=doc_title,
            target_language=target_language,
            prompt_hash=prompt_hash,
        )

        logger.info("🚀 Iniciando ejecución streaming del grafo para doc='%s'...", doc_title)
        # Accumulate the per-node updates so the final response can be read
        # without a second (expensive) execution.
        final_state: Dict[str, Any] = dict(initial_state)
        async for chunk in self.graph.astream(initial_state, stream_mode="updates"):
            for node_name, update in chunk.items():
                if isinstance(update, dict):
                    final_state.update(update)
                yield {"stage": node_name}

        final_response = final_state.get("final_response")
        if not final_response:
            logger.warning("El grafo no produjo final_response directamente; ejecutando formatter de respaldo.")
            final_response = self._node_formatter(final_state)["final_response"]

        logger.info(
            "🎉 LangGraph streaming completado. Nodos ejecutados: %s",
            final_response.metadata.graph_nodes_executed,
        )
        yield {"stage": "done", "response": final_response}
