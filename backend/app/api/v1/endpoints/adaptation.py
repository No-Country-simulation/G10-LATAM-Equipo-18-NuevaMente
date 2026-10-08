"""
adaptation.py

Purpose:
    FastAPI router for educational content adaptation requests.
    Runs in-memory hybrid retrieval (dense + BM25 + RRF), cross-encoder
    reranking (Jina/Cohere), and multi-agent orchestration (Planner, Writer,
    Auditor) to produce structured pedagogical output.

Input:
    AdaptationRequest payload via HTTP POST.

Output:
    AdaptationResponse with structured educational artifacts and storage metadata.
"""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.timer import PipelineTracer
from app.schemas.adaptation import AdaptationRequest, AdaptationResponse
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.document_index_cache import DocumentIndexCache
from app.services.embedding_service import EmbeddingService
from app.services.ingester_service import IngesterService
from app.services.reranker_service import get_default_rerankers
from rank_bm25 import BM25Okapi
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter()

ingester_service = IngesterService()
embedding_service = EmbeddingService()
agent_orchestrator = AgentOrchestrator()
index_cache = DocumentIndexCache()


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def _retrieve_passages_inline(
    query: str,
    child_chunks: List[Dict[str, Any]],
    parent_chunks: List[Dict[str, Any]],
    top_k: int = 5,
    rerank_pool_size: int = 10,
) -> List[Dict[str, Any]]:
    """
    Executes in-memory hybrid retrieval (dense + lexical BM25 + RRF)
    resolved to unique parent passages and ranked using reranker_service.
    """
    if not child_chunks:
        return parent_chunks[:top_k]

    # 1. Dense retrieval (vector similarity)
    query_embedding = embedding_service.embed_text(query, is_query=True)

    missing_indices = [i for i, child in enumerate(child_chunks) if not child.get("embedding")]
    if missing_indices:
        missing_texts = [child_chunks[i]["content"] for i in missing_indices]
        computed_embeddings = embedding_service.embed_batch(missing_texts, is_query=False)
        if isinstance(computed_embeddings, list):
            for i, emb in zip(missing_indices, computed_embeddings):
                child_chunks[i]["embedding"] = emb

    dense_results = []
    for i, child in enumerate(child_chunks):
        chunk_embedding = child.get("embedding") or embedding_service.embed_text(child["content"], is_query=False)
        score = _cosine_similarity(query_embedding, chunk_embedding)
        dense_results.append((i, score))

    dense_results.sort(key=lambda x: x[1], reverse=True)
    dense_ranks = {idx: rank for rank, (idx, _) in enumerate(dense_results)}

    # 2. Lexical retrieval (BM25)
    tokenized_corpus = [child["content"].lower().split() for child in child_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())

    lexical_results = [(i, score) for i, score in enumerate(bm25_scores)]
    lexical_results.sort(key=lambda x: x[1], reverse=True)
    lexical_ranks = {idx: rank for rank, (idx, _) in enumerate(lexical_results)}

    # 3. Reciprocal Rank Fusion (RRF)
    rrf_k = 60
    rrf_results = []
    for i in range(len(child_chunks)):
        score = 1.0 / (rrf_k + dense_ranks[i]) + 1.0 / (rrf_k + lexical_ranks[i])
        rrf_results.append((i, score))

    rrf_results.sort(key=lambda x: x[1], reverse=True)
    top_children_indices = [idx for idx, _ in rrf_results[:rerank_pool_size]]

    # 4. Map top child chunks to unique parent chunks
    parent_dict = {p["id"]: p for p in parent_chunks}
    selected_parent_ids = set()
    candidate_parents = []
    for child_idx in top_children_indices:
        child = child_chunks[child_idx]
        pid = child.get("parent_id") or child.get("id")
        if pid and pid in parent_dict and pid not in selected_parent_ids:
            selected_parent_ids.add(pid)
            candidate_parents.append(parent_dict[pid].copy())

    if not candidate_parents:
        return parent_chunks[:top_k]

    # 5. Cross-Encoder reranking via reranker_service
    documents = [p["content"] for p in candidate_parents]
    rerankers = get_default_rerankers()

    for reranker in rerankers:
        try:
            results = reranker.rerank(query=query, documents=documents, top_n=top_k)
            reranked_parents = []
            for result in results:
                parent = candidate_parents[result["index"]].copy()
                parent["relevance_score"] = round(result["relevance_score"], 4)
                reranked_parents.append(parent)
            return reranked_parents
        except Exception as exc:
            logger.warning(
                "Reranker %s failed: %s. Trying next provider.",
                type(reranker).__name__,
                exc,
            )

    logger.warning("All rerankers failed; returning top RRF candidates.")
    return candidate_parents[:top_k]


@router.post("/adapt-content", response_model=AdaptationResponse, status_code=status.HTTP_200_OK)
async def adapt_content(request: AdaptationRequest):
    """
    Main adaptation endpoint: parses document content, runs hybrid retrieval with reranking,
    and orchestrates pedagogical content generation through multi-agent workflows.
    """
    tracer = PipelineTracer()
    try:
        raw_title = request.title or request.documento_titulo or "Documento"
        raw_content = request.content or request.documento_contenido or ""

        doc_hash = index_cache.compute_doc_hash(raw_title, raw_content)
        cached_index = index_cache.get_indexed_document(doc_hash)

        if cached_index:
            doc_data = cached_index["doc_data"]
            key_concepts = cached_index.get("key_concepts", [])
            prerequisites = cached_index.get("prerequisites", [])
            tracer.timings["ingesta_extraccion"] = 0.0
            tracer.timings["chunking"] = 0.0
            tracer.record_embedding_call(len(doc_data["child_chunks"]), len(doc_data["child_chunks"]))
        else:
            doc_lock = index_cache.get_doc_lock(doc_hash)
            with doc_lock:
                cached_index = index_cache.get_indexed_document(doc_hash)
                if cached_index:
                    doc_data = cached_index["doc_data"]
                    key_concepts = cached_index.get("key_concepts", [])
                    prerequisites = cached_index.get("prerequisites", [])
                    tracer.timings["ingesta_extraccion"] = 0.0
                    tracer.timings["chunking"] = 0.0
                    tracer.record_embedding_call(len(doc_data["child_chunks"]), len(doc_data["child_chunks"]))
                else:
                    # 1. Document parsing and AST segmentation
                    tracer.start_stage("ingesta_extraccion")
                    target_chunk_size = request.chunk_size or 500
                    custom_ingester = IngesterService(child_chunk_size=target_chunk_size)
                    doc_data = custom_ingester.parse_and_chunk_document(
                        content=raw_content,
                        title=raw_title,
                    )
                    tracer.end_stage("ingesta_extraccion")
                    tracer.timings["chunking"] = 0.0

                    key_concepts = []
                    prerequisites = []

                    index_cache.set_indexed_document(doc_hash, {
                        "doc_data": doc_data,
                        "key_concepts": key_concepts,
                        "prerequisites": prerequisites,
                    })
                    tracer.record_embedding_call(len(doc_data["child_chunks"]), 0)

        # 2. Hybrid RAG retrieval + Reranking
        tracer.start_stage("recuperacion_hybrid")
        query_text = f"{request.recipient_profile} {request.output_format} {request.niche}"
        top_passages = _retrieve_passages_inline(
            query=query_text,
            child_chunks=doc_data["child_chunks"],
            parent_chunks=doc_data["parent_chunks"],
            top_k=settings.MAX_TOP_K_CHUNKS,
            rerank_pool_size=settings.RAG_RERANK_POOL_SIZE,
        )
        tracer.end_stage("recuperacion_hybrid")

        # 3. Agentic Orchestration with Planner, Writer, Auditor
        response = await agent_orchestrator.run_pipeline(
            request=request,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites,
            tracer=tracer,
        )

        return response

    except Exception as error:
        logger.exception("Error during content adaptation pipeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content adaptation pipeline error: {str(error)}",
        )
