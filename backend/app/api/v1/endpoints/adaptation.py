"""
adaptation.py

Purpose:
    FastAPI router handling educational content adaptation requests.
    Integrates Layout-Aware ingestion, LangGraph multi-agent orchestration,
    and OCI Object Storage persistence.

Input:
    AdaptationRequest payload via HTTP POST.

Output:
    AdaptationResponse with structured educational artifacts and OCI storage metadata.
"""

import math
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from rank_bm25 import BM25Okapi

from app.schemas.adaptation import AdaptationRequest, AdaptationResponse
from app.services.ingester_service import IngesterService
from app.services.langgraph_orchestrator import LangGraphOrchestrator
from app.services.pipeline_stages import QUANTITY_TABLE
from app.services.text_cleaner import clean_text
from app.core.timer import PipelineTracer

logger = logging.getLogger("AdaptationEndpoint")
router = APIRouter()
langgraph_orchestrator = LangGraphOrchestrator()
ingester_service = IngesterService()


@router.post("/adapt-content", response_model=AdaptationResponse, status_code=status.HTTP_200_OK)
async def adapt_content(request: AdaptationRequest):
    """
    Main adaptation endpoint: receives technical content and personalization options,
    runs LangGraph multi-agent orchestration, and returns structured educational
    package saved to OCI Object Storage Always Free and local catalog.
    """
    tracer = PipelineTracer()
    try:
        raw_content = request.content or ""
        cleaned = clean_text(raw_content)
        request.content = cleaned

        # Ingest and chunk text if parent chunks not already available
        tracer.start_stage("ingesta_extraccion")
        ingested_doc = ingester_service.process_text(
            cleaned,
            title=request.title or "Documento Técnico",
        )
        rag_payload = ingester_service.build_rag_chunks(ingested_doc)
        parent_chunks = rag_payload["parent_chunks"]
        child_chunks = rag_payload["child_chunks"]
        tracer.end_stage("ingesta_extraccion")

        # Rank passages using lexical search over chunks
        tracer.start_stage("recuperacion_hybrid")
        top_passages: List[Dict[str, Any]] = []
        if child_chunks:
            tokenized_corpus = [chunk["content"].lower().split() for chunk in child_chunks]
            bm25 = BM25Okapi(tokenized_corpus)
            query_str = f"{request.recipient_profile or ''} {request.output_format or ''} {request.niche or ''}".strip()
            query_tokens = query_str.lower().split() if query_str else ["conceptos"]
            scores = bm25.get_scores(query_tokens)
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

            seen_parents = set()
            for idx in ranked_indices:
                p_id = child_chunks[idx].get("parent_id")
                if p_id and p_id not in seen_parents:
                    seen_parents.add(p_id)
                    for p in parent_chunks:
                        if p["id"] == p_id:
                            top_passages.append(p)
                            break
                if len(top_passages) >= 12:
                    break

        if not top_passages:
            top_passages = parent_chunks[:12] if parent_chunks else [{"id": "p0", "content": cleaned, "metadata": {}}]
        tracer.end_stage("recuperacion_hybrid")

        # LangGraph Multi-Agent Orchestration
        response = await langgraph_orchestrator.run_pipeline(
            request=request,
            top_passages=top_passages,
            key_concepts=[],
            prerequisites=[],
            all_parent_chunks=parent_chunks or top_passages,
            tracer=tracer,
            document_id=getattr(request, "document_id", None),
        )

        return response

    except Exception as error:
        logger.exception("Error en la adaptación de contenido: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la adaptación de contenido: {str(error)}",
        )


@router.post("/adapt-content/ampliar/{content_id}", response_model=AdaptationResponse, status_code=status.HTTP_200_OK)
async def ampliar_content(content_id: str, request: AdaptationRequest):
    """
    Amplía un contenido educativo existente incrementando la versión a v{n+1}.json
    sin sobrescribir la versión previa en OCI Object Storage Always Free.
    """
    from app.services.storage_queue_service import StorageQueueService
    status_info = StorageQueueService.get_instance().get_content_status(content_id)
    curr_version = status_info.get("version", 1) or 1
    next_version = curr_version + 1

    setattr(request, "version", next_version)
    return await adapt_content(request)
