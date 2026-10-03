import math
import numpy as np
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import cohere
import logging

from app.core.config import settings
from app.services.embedding_service import EmbeddingService

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

from app.infrastructure.cohere_client import CohereClient

class HybridRAGService:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.co_client = CohereClient()

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

    def _map_to_parents(self, children: List[Dict[str, Any]], parent_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mapea fragmentos hijos a sus correspondientes bloques padres."""
        parent_dict = {p["id"]: p for p in parent_chunks}
        selected_parent_ids = set()
        candidates = []
        for child in children:
            pid = child.get("parent_id") or child.get("id")
            if pid and pid in parent_dict and pid not in selected_parent_ids:
                selected_parent_ids.add(pid)
                candidates.append(parent_dict[pid].copy())
        return candidates

    def retrieve_top_passages(
        self,
        query: str,
        child_chunks: List[Dict[str, Any]],
        parent_chunks: List[Dict[str, Any]],
        top_k: int = 5,
        rerank_top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la búsqueda híbrida (Dense + Léxica BM25), aplica Reciprocal Rank Fusion (RRF),
        y realiza un reordenamiento final usando Cohere Reranker.
        """
        if not child_chunks:
            return parent_chunks[:top_k]

        # ---------------------------------------------------------
        # 1. Búsqueda Densa (Embeddings + Similitud Coseno)
        # ---------------------------------------------------------
        # Generamos el vector de la pregunta (purificamos antes de comparar)
        query_embedding = self.embedding_service.embed_text(query, is_query=True)
        
        dense_results = []
        for i, child in enumerate(child_chunks):
            # IDEALMENTE: child["embedding"] ya viene de la BD Vectorial.
            chunk_embedding = child.get("embedding")
            if not chunk_embedding:
                # Si no está en BD, lo calculamos en caliente (solo como fallback)
                chunk_embedding = self.embedding_service.embed_text(child["content"], is_query=False)
            
            score = cosine_similarity(query_embedding, chunk_embedding)
            dense_results.append((i, score))
            
        # Ordenamos y sacamos los rankings (mayor score = mejor rank, rank empieza en 0)
        dense_results.sort(key=lambda x: x[1], reverse=True)
        dense_ranks = {idx: rank for rank, (idx, score) in enumerate(dense_results)}
        
        # ---------------------------------------------------------
        # 2. Búsqueda Léxica (BM25 Real)
        # ---------------------------------------------------------
        tokenized_corpus = [child["content"].lower().split() for child in child_chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)
        
        lexical_results = [(i, score) for i, score in enumerate(bm25_scores)]
        lexical_results.sort(key=lambda x: x[1], reverse=True)
        lexical_ranks = {idx: rank for rank, (idx, score) in enumerate(lexical_results)}
        
        # ---------------------------------------------------------
        # 3. Reciprocal Rank Fusion (RRF)
        # ---------------------------------------------------------
        rrf_results = []
        k_rrf = 60 # Constante estándar para RRF
        for i in range(len(child_chunks)):
            # Calculamos RRF usando las posiciones, no los scores en bruto.
            rrf_score = 1.0 / (k_rrf + dense_ranks[i]) + 1.0 / (k_rrf + lexical_ranks[i])
            rrf_results.append((i, rrf_score))
            
        # Ordenamos los child_chunks según su puntaje RRF
        rrf_results.sort(key=lambda x: x[1], reverse=True)
        
        # Tomamos el Top N de Hijos (antes del reranking, ej: 10)
        top_n_children_indices = [idx for idx, score in rrf_results[:rerank_top_k]]
        
        # ---------------------------------------------------------
        # 4. Mapeo a Parent Chunks (Parent-Document Retrieval)
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
        
        # Si no tenemos API de Cohere o no hay candidatos, devolvemos el resultado de RRF
        if not getattr(self.co_client, "client", None) or len(candidates_for_rerank) == 0:
            return candidates_for_rerank[:top_k]
            
        # ---------------------------------------------------------
        # 5. Reranking Final (Cohere)
        # ---------------------------------------------------------
        # Le enviamos al Cross-Encoder los chunks PADRES para que entienda todo el contexto.
        docs_to_rerank = [p["content"] for p in candidates_for_rerank]
        
        try:
            # Usamos el modelo multilingüe que es excelente para español
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
            logger.error("Error al usar Cohere Reranker: %s. Cayendo a resultados RRF puros.", e)
            return candidates_for_rerank[:top_k]
