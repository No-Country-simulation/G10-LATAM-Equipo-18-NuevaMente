"""
retrieval_service.py

Purpose:
    Retrieval stage of the RAG pipeline for a single document: dense search
    (via the document's FAISS store) + lexical BM25, fused with Reciprocal
    Rank Fusion (RRF), resolved to unique parent chunks, and reranked
    (Jina, falling back to Cohere) for a final relevance-ordered list.

    This stage only returns text — it never calls an LLM. Content generation
    is a separate stage (agent_orchestrator / the LangGraph pipeline) that
    consumes this service's output.

Input:
    - document_id (str): which document's FAISS store to search.
    - query (str): an internally-built search query (there is no free-form
      user search in this app — queries are derived from profile/format/niche).
    - top_k (int): how many parent chunks to return after reranking.

Output:
    - List[Dict[str, Any]]: parent chunks ordered by final relevance, each
      with a "relevance_score" field.
"""

import logging
from typing import Any, Dict, List, Tuple

from rank_bm25 import BM25Okapi

from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import get_store
from app.services.reranker_service import BaseReranker, get_default_rerankers

logger = logging.getLogger(__name__)

# Standard RRF smoothing constant — dampens the impact of any single rank
# position without needing to tune it per document.
_RRF_K = 60


# In-process BM25 cache: rebuilding the index per query is wasted work once a
# document's chunk count hasn't changed since the last query. Not shared
# across processes — consistent with the vector store's own cache in
# vector_store_service.py, and fine at hackathon scale.
_bm25_cache: Dict[str, Tuple[int, BM25Okapi]] = {}


def _get_bm25_index(document_id: str, child_chunks: List[Dict[str, Any]]) -> BM25Okapi:
    """Returns a cached BM25 index for this document, rebuilding it only if
    the indexed chunk count changed since the last call."""
    cached = _bm25_cache.get(document_id)
    if cached is not None and cached[0] == len(child_chunks):
        return cached[1]

    tokenized_corpus = [chunk["content"].lower().split() for chunk in child_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    _bm25_cache[document_id] = (len(child_chunks), bm25)
    return bm25


class RetrievalService:
    """
    Retrieves and ranks passages from a single document's already-built
    FAISS store. Does not embed or index documents itself — that happens
    earlier in the pipeline (IngesterService + EmbeddingService + get_store).
    """

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        # Constructed lazily on first use — a provider missing its API key
        # shouldn't break retrieval for documents that never need reranking.
        self._rerankers: List[BaseReranker] = None

    def _get_rerankers(self) -> List[BaseReranker]:
        if self._rerankers is None:
            self._rerankers = get_default_rerankers()
        return self._rerankers

    def retrieve(
        self,
        document_id: str,
        query: str,
        top_k: int = 5,
        rerank_pool_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Runs the full retrieval pipeline for one document and returns the
        top_k parent chunks most relevant to the query.
        """
        store = get_store(document_id)
        if store.index is None or store.index.ntotal == 0:
            logger.warning("No indexed chunks for document_id=%s.", document_id)
            return []

        child_chunks = store.child_documents
        id_to_position = {chunk["id"]: i for i, chunk in enumerate(child_chunks)}

        dense_ranks = self._dense_ranks(query, store, id_to_position)
        lexical_ranks = self._lexical_ranks(document_id, query, child_chunks)

        fused_order = self._fuse_rrf(len(child_chunks), dense_ranks, lexical_ranks)
        candidates = self._resolve_unique_parents(
            fused_order, child_chunks, store.parent_documents, rerank_pool_size
        )

        if not candidates:
            return []

        return self._rerank(query, candidates, top_k)

    # ── Dense + lexical ranking ────────────────────────────────────────────────

    def _dense_ranks(
        self,
        query: str,
        store,
        id_to_position: Dict[str, int],
    ) -> Dict[int, int]:
        """Ranks every indexed child chunk by cosine similarity to the query,
        via the document's own FAISS store — no embeddings are recomputed here."""
        query_model = store.model_name or self.embedding_service.model_name
        query_embedding = self.embedding_service.embed_text(
            query, is_query=True, model_name=query_model
        )
        ranked_hits = store.similarity_search(
            query_embedding=query_embedding,
            query_model_name=query_model,
            top_k=len(id_to_position),
        )
        return {
            id_to_position[hit["id"]]: rank
            for rank, hit in enumerate(ranked_hits)
        }

    def _lexical_ranks(
        self,
        document_id: str,
        query: str,
        child_chunks: List[Dict[str, Any]],
    ) -> Dict[int, int]:
        """Ranks every child chunk by BM25 lexical score against the query."""
        bm25 = _get_bm25_index(document_id, child_chunks)
        scores = bm25.get_scores(query.lower().split())
        ranked_positions = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return {position: rank for rank, position in enumerate(ranked_positions)}

    @staticmethod
    def _fuse_rrf(
        total_chunks: int,
        dense_ranks: Dict[int, int],
        lexical_ranks: Dict[int, int],
    ) -> List[int]:
        """Combines dense and lexical rankings via Reciprocal Rank Fusion,
        using rank position (not raw scores, which aren't comparable across
        the two methods)."""
        fused_scores = []
        for position in range(total_chunks):
            dense_component = 1.0 / (_RRF_K + dense_ranks.get(position, total_chunks))
            lexical_component = 1.0 / (_RRF_K + lexical_ranks.get(position, total_chunks))
            fused_scores.append((position, dense_component + lexical_component))

        fused_scores.sort(key=lambda item: item[1], reverse=True)
        return [position for position, _ in fused_scores]

    # ── Parent resolution ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_unique_parents(
        fused_order: List[int],
        child_chunks: List[Dict[str, Any]],
        parent_documents: Dict[str, Dict[str, Any]],
        pool_size: int,
    ) -> List[Dict[str, Any]]:
        """Walks the fused child ranking and collects each unique parent
        chunk once, in ranked order, up to pool_size candidates."""
        seen_parent_ids = set()
        candidates: List[Dict[str, Any]] = []

        for position in fused_order:
            parent_id = child_chunks[position].get("parent_id")
            if not parent_id or parent_id in seen_parent_ids:
                continue

            parent = parent_documents.get(parent_id)
            if parent:
                seen_parent_ids.add(parent_id)
                candidates.append(parent.copy())

            if len(candidates) >= pool_size:
                break

        return candidates

    # ── Reranking ──────────────────────────────────────────────────────────────

    def _rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Tries each reranker in order (Jina, then Cohere). Falls back to
        the RRF order — unchanged — only if every reranker fails."""
        documents = [candidate["content"] for candidate in candidates]

        for reranker in self._get_rerankers():
            try:
                results = reranker.rerank(query=query, documents=documents, top_n=top_k)
                reranked = []
                for result in results:
                    parent = candidates[result["index"]].copy()
                    parent["relevance_score"] = round(result["relevance_score"], 4)
                    reranked.append(parent)
                return reranked
            except Exception as exc:
                logger.warning(
                    "Reranker %s failed (%s). Trying next provider.",
                    type(reranker).__name__, exc,
                )

        logger.warning("All rerankers failed. Falling back to RRF order.")
        return candidates[:top_k]


def retrieve_context(
    document_id: str,
    query: str,
    top_k: int = 5,
    embedding_service: Optional[EmbeddingService] = None,
) -> List[Dict[str, Any]]:
    """Convenience function running retrieval with default EmbeddingService."""
    svc = embedding_service or EmbeddingService()
    retrieval_svc = RetrievalService(embedding_service=svc)
    return retrieval_svc.retrieve(document_id=document_id, query=query, top_k=top_k)