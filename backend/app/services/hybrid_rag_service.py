import math
import logging
import numpy as np
from typing import List, Dict, Any

import cohere
from rank_bm25 import BM25Okapi
from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.infrastructure.cohere_client import CohereClient


logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calcula la Similitud Coseno entre dos vectores."""
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


class HybridRAGService:
    """
    Servicio RAG Híbrido Avanzado (LangChain / Docling Data Ecosystem Architecture):
    - Multi-Query Expansion (Generación de sub-consultas sintéticas)
    - Búsqueda Densa (Vector Embeddings) + Léxica (BM25Okapi)
    - Reciprocal Rank Fusion (RRF)
    - Document Compression & Deduplication (Compresión de contexto)
    - Cohere Cross-Encoder Reranking Multilingüe (v3.0)
    """

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.co_client = CohereClient()

    def generate_multi_queries(self, original_query: str) -> List[str]:
        """
        Multi-Query Expansion (Figura 2): Expande la pregunta original en
        variantes conceptuales para elevar la precisión de recuperación.
        """
        queries = [original_query]
        # Generar variaciones léxicas sin llamadas costosas si la consulta es larga
        words = original_query.strip().split()
        if len(words) > 3:
            queries.append(" ".join(words[:4]))
            queries.append(" ".join(words[2:]))
        return list(dict.fromkeys(queries))

    def compress_retrieved_context(self, parent_chunks: List[Dict[str, Any]], max_chars: int = 4000) -> str:
        """
        Document Compressor (Figura 2): Filtra redundancias y comprime los pasajes
        recuperados en un único bloque de contexto de alta densidad de información.
        """
        seen_lines = set()
        compressed_text = []

        for chunk in parent_chunks:
            title = chunk.get("title", "")
            content = chunk.get("content", "")
            
            if title:
                compressed_text.append(f"### {title}")
                
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped and stripped not in seen_lines:
                    seen_lines.add(stripped)
                    compressed_text.append(stripped)

            if sum(len(t) for t in compressed_text) >= max_chars:
                break

        return "\n\n".join(compressed_text)

    def _rrf(self, lexical: List[Dict[str, Any]], dense: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion entre listas de resultados léxicos y densos."""
        scores: Dict[str, float] = {}
        items_by_id: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(lexical):
            item_id = item.get("id") or item.get("parent_id") or str(rank)
            scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank))
            if item_id not in items_by_id:
                items_by_id[item_id] = item.copy()

        for rank, item in enumerate(dense):
            item_id = item.get("id") or item.get("parent_id") or str(rank)
            scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank))
            if item_id not in items_by_id:
                items_by_id[item_id] = item.copy()

        fused = []
        for item_id, score in scores.items():
            elem = items_by_id[item_id].copy()
            elem["rrf_score"] = score
            fused.append(elem)

        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused

    def retrieve_top_passages(
        self,
        query: str,
        child_chunks: List[Dict[str, Any]],
        parent_chunks: List[Dict[str, Any]],
        top_k: int = 5,
        rerank_top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la búsqueda híbrida (Dense + Léxica BM25) con Multi-Query Expansion,
        aplica Reciprocal Rank Fusion (RRF), y realiza un reordenamiento final usando Cohere Reranker.
        """
        if not child_chunks:
            return parent_chunks[:top_k]

        # Multi-Query Expansion
        multi_queries = self.generate_multi_queries(query)

        # ---------------------------------------------------------
        # 1. Búsqueda Densa (Embeddings + Similitud Coseno acumulada)
        # ---------------------------------------------------------
        dense_scores_accumulator = np.zeros(len(child_chunks))

        for q in multi_queries:
            query_embedding = self.embedding_service.embed_text(q, is_query=True)
            for i, child in enumerate(child_chunks):
                chunk_embedding = child.get("embedding")
                if not chunk_embedding:
                    chunk_embedding = self.embedding_service.embed_text(child["content"], is_query=False)
                score = cosine_similarity(query_embedding, chunk_embedding)
                dense_scores_accumulator[i] += score

        dense_results = [(i, dense_scores_accumulator[i] / len(multi_queries)) for i in range(len(child_chunks))]
        dense_results.sort(key=lambda x: x[1], reverse=True)
        dense_ranks = {idx: rank for rank, (idx, score) in enumerate(dense_results)}

        # ---------------------------------------------------------
        # 2. Búsqueda Léxica (BM25Okapi)
        # ---------------------------------------------------------
        tokenized_corpus = [child["content"].lower().split() for child in child_chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        lexical_scores_accumulator = np.zeros(len(child_chunks))
        for q in multi_queries:
            query_tokens = q.lower().split()
            bm25_scores = bm25.get_scores(query_tokens)
            lexical_scores_accumulator += np.array(bm25_scores)

        lexical_results = [(i, lexical_scores_accumulator[i]) for i in range(len(child_chunks))]
        lexical_results.sort(key=lambda x: x[1], reverse=True)
        lexical_ranks = {idx: rank for rank, (idx, score) in enumerate(lexical_results)}

        # ---------------------------------------------------------
        # 3. Reciprocal Rank Fusion (RRF)
        # ---------------------------------------------------------
        rrf_results = []
        k_rrf = 60
        for i in range(len(child_chunks)):
            rrf_score = 1.0 / (k_rrf + dense_ranks[i]) + 1.0 / (k_rrf + lexical_ranks[i])
            rrf_results.append((i, rrf_score))

        rrf_results.sort(key=lambda x: x[1], reverse=True)

        top_n_children_indices = [idx for idx, score in rrf_results[:rerank_top_k]]

        # ---------------------------------------------------------
        # 4. Parent Document Mapping
        # ---------------------------------------------------------
        selected_parent_ids = set()
        candidates_for_rerank = []
        parent_dict = {p["id"]: p for p in parent_chunks}

        for child_idx in top_n_children_indices:
            child = child_chunks[child_idx]
            pid = child["parent_id"]
            if pid not in selected_parent_ids and pid in parent_dict:
                selected_parent_ids.add(pid)
                parent_obj = parent_dict[pid].copy()
                candidates_for_rerank.append(parent_obj)

        if not getattr(self.co_client, "client", None) or len(candidates_for_rerank) == 0:
            return candidates_for_rerank[:top_k]

        # ---------------------------------------------------------
        # 5. Cohere Cross-Encoder Reranking
        # ---------------------------------------------------------
        docs_to_rerank = [p["content"] for p in candidates_for_rerank]

        try:
            rerank_response = self.co_client.rerank(
                model="rerank-multilingual-v3.0",
                query=query,
                documents=docs_to_rerank,
                top_n=top_k
            )

            final_parents = []
            for result in rerank_response.results:
                original_parent = candidates_for_rerank[result.index]
                original_parent["relevance_score"] = round(result.relevance_score, 4)
                final_parents.append(original_parent)

            return final_parents

        except Exception as e:
            logger.error("Error en Cohere Reranker: %s. Retornando pasajes RRF.", e)
            return candidates_for_rerank[:top_k]
