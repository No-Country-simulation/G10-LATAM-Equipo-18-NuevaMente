"""
adaptation.py

Purpose:
    FastAPI router handling educational content adaptation requests.
    Integrates Layout-Aware ingestion, Graph RAG, Hybrid RAG,
    and Gemini agent orchestration.

Input:
    AdaptationRequest payload via HTTP POST.

Output:
    AdaptationResponse with structured educational artifacts and OCI storage metadata.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.adaptation import AdaptationRequest, AdaptationResponse
from app.services.ingester_service import IngesterService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.graph_rag_service import GraphRAGService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.embedding_service import EmbeddingService

from app.core.timer import PipelineTracer
from app.services.text_cleaner import clean_text
from app.services.document_index_cache import DocumentIndexCache
from app.services.agent_orchestrator import QUANTITY_TABLE
import math

router = APIRouter()

ingester_service = IngesterService()
embedding_service = EmbeddingService()
hybrid_rag_service = HybridRAGService(embedding_service=embedding_service)
graph_rag_service = GraphRAGService()
agent_orchestrator = AgentOrchestrator()
index_cache = DocumentIndexCache()


@router.post("/adapt-content", response_model=AdaptationResponse, status_code=status.HTTP_200_OK)
async def adapt_content(request: AdaptationRequest):
    """
    Main adaptation endpoint: receives technical content and personalization options,
    runs Graph RAG + Hybrid RAG + Gemini Agent Orchestration, and returns
    structured educational package saved to OCI Object Storage Always Free.
    """
    tracer = PipelineTracer()
    try:
        # Sanitize incoming document content immediately
        raw_content = request.content or ""
        cleaned = clean_text(raw_content)
        request.content = cleaned

        doc_hash = index_cache.compute_doc_hash(request.title, cleaned)
        cached_index = index_cache.get_indexed_document(doc_hash)

        if cached_index:
            parent_chunks = cached_index.get("doc_data", {}).get("parent_chunks", [])
            has_garbage = any(
                "FlateDecode" in p.get("content", "") or "stream" in p.get("content", "") or "\ufffd" in p.get("content", "")
                for p in parent_chunks
            )
            if has_garbage:
                cached_index = None

        if cached_index:
            doc_data = cached_index["doc_data"]
            key_concepts = cached_index["key_concepts"]
            prerequisites = cached_index["prerequisites"]
            tracer.timings["ingesta_extraccion"] = 0.0
            tracer.timings["chunking"] = 0.0
            tracer.timings["graph_rag"] = 0.0
            tracer.record_embedding_call(len(doc_data["child_chunks"]), len(doc_data["child_chunks"]))
        else:
            doc_lock = index_cache.get_doc_lock(doc_hash)
            with doc_lock:
                # Double check after acquiring lock
                cached_index = index_cache.get_indexed_document(doc_hash)
                if cached_index:
                    doc_data = cached_index["doc_data"]
                    key_concepts = cached_index["key_concepts"]
                    prerequisites = cached_index["prerequisites"]
                    tracer.timings["ingesta_extraccion"] = 0.0
                    tracer.timings["chunking"] = 0.0
                    tracer.timings["graph_rag"] = 0.0
                    tracer.record_embedding_call(len(doc_data["child_chunks"]), len(doc_data["child_chunks"]))
                else:
                    # 1. Document parsing and AST segmentation with dynamic chunk size
                    tracer.start_stage("ingesta_extraccion")
                    target_chunk_size = request.chunk_size or 500
                    custom_ingester = IngesterService(child_chunk_size=target_chunk_size)
                    doc_data = custom_ingester.parse_and_chunk_document(
                        content=request.content,
                        title=request.title,
                    )
                    tracer.end_stage("ingesta_extraccion")
                    tracer.timings["chunking"] = 0.0  # Included in ingesta_extraccion

                    # 2. Graph RAG (Extract Key Concepts & Prerequisites via DAG)
                    tracer.start_stage("graph_rag")
                    _, key_concepts, prerequisites = graph_rag_service.build_concept_dag(request.content)
                    tracer.end_stage("graph_rag")

                    index_cache.set_indexed_document(doc_hash, {
                        "doc_data": doc_data,
                        "key_concepts": key_concepts,
                        "prerequisites": prerequisites
                    })
                    tracer.record_embedding_call(len(doc_data["child_chunks"]), 0)

        # 3. Hybrid RAG (BM25 + Dense Embeddings + Cross-Encoder Re-ranker)
        fmt_key = (request.output_format or "flashcards").lower()
        lvl_key = (request.quantity_level or "estandar").lower()
        base_target = QUANTITY_TABLE.get(fmt_key, {}).get(lvl_key, 20)
        target_qty = request.target_quantity if request.target_quantity is not None else (
            base_target if request.quantity_level else (request.quantity or base_target)
        )
        total_parents = len(doc_data.get("parent_chunks", []))
        dynamic_top_k = max(10, min(total_parents, math.ceil(target_qty / 2))) if total_parents > 0 else 10

        tracer.start_stage("recuperacion_hybrid")
        top_passages = hybrid_rag_service.retrieve_top_passages(
            query=f"{request.recipient_profile} {request.output_format} {request.niche}",
            child_chunks=doc_data["child_chunks"],
            parent_chunks=doc_data["parent_chunks"],
            top_k=dynamic_top_k,
        )
        tracer.end_stage("recuperacion_hybrid")

        # 4. Agentic Orchestration with Gemini
        response = await agent_orchestrator.run_pipeline(
            request=request,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites,
            tracer=tracer,
        )

        return response

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la adaptación de contenido: {str(error)}",
        )
