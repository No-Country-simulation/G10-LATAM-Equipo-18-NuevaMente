"""
vector_store_service.py

Purpose:
    Provides abstract and concrete vector store implementations for indexing,
    persisting, and querying document embeddings. Manages mathematical index
    operations (using FAISS cosine similarity) alongside metadata storage
    and model compatibility tracking. Designed to allow seamless substitution
    with alternative stores such as Supabase (pgvector).

    Also exposes a factory (get_store / save_store) that gives each document
    its own FAISS index under VECTOR_STORE_DIR/{document_id}/, since content
    generation always works against a single document — never a cross-
    document search — so indexes never need to mix documents together.

Input:
    - Text chunks and metadata produced by IngesterService.
    - Vector embeddings produced by EmbeddingService.
    - Query vector and query model identifier for retrieval.
    - document_id, to resolve which per-document index to open (factory only).

Output:
    - Ranked search results (child chunks with similarity scores).
    - Resolved parent document chunks for context assembly.
    - Serialized vector index and metadata on local disk.
"""

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class IncompatibleEmbeddingModelError(ValueError):
    """Raised when query embedding model does not match the index model."""
    pass


class BaseVectorStore(ABC):
    """
    Abstract interface defining vector store operations. Guarantees consistency
    between local in-memory engines (e.g. FAISS) and remote engines (e.g. Supabase).
    """

    @abstractmethod
    def add_documents(
        self,
        child_chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        parent_chunks: Optional[List[Dict[str, Any]]] = None,
        model_name: str = "",
    ) -> None:
        """Indexes child chunk vectors and records parent/child relationship metadata."""
        pass

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: List[float],
        query_model_name: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Finds top-k child chunks matching the query embedding."""
        pass

    @abstractmethod
    def retrieve_parent_chunks(
        self,
        query_embedding: List[float],
        query_model_name: str,
        top_k_parents: int = 3,
    ) -> List[Dict[str, Any]]:
        """Identifies top parent chunks corresponding to the most relevant child chunks."""
        pass

    @abstractmethod
    def save(self, directory_path: str) -> None:
        """Serializes vector index and metadata to persistent storage."""
        pass

    @abstractmethod
    def load(self, directory_path: str) -> None:
        """Deserializes vector index and metadata from persistent storage."""
        pass


class FAISSVectorStore(BaseVectorStore):
    """
    FAISS-based implementation of BaseVectorStore. Uses an IndexFlatIP index
    operating on L2-normalized vectors to provide exact cosine similarity search.
    """

    def __init__(self, dimension: Optional[int] = None, model_name: Optional[str] = None):
        self.dimension = dimension
        self.model_name = model_name or ""
        self.index = None
        self.child_documents: List[Dict[str, Any]] = []
        self.parent_documents: Dict[str, Dict[str, Any]] = {}

        if self.dimension:
            self._initialize_index(self.dimension)

    def _initialize_index(self, dimension: int) -> None:
        """Initializes a FAISS inner product index for normalized vectors."""
        import faiss  # Lazy import for modularity

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """L2-normalizes vectors so inner product corresponds to cosine similarity."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        # Avoid division by zero for empty or null vectors
        norms[norms == 0.0] = 1.0
        return vectors / norms

    def add_documents(
        self,
        child_chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        parent_chunks: Optional[List[Dict[str, Any]]] = None,
        model_name: str = "",
    ) -> None:
        """
        Validates model compatibility, normalizes embedding vectors, and
        stores both vectors in the FAISS index and chunk payloads in memory.
        """
        if not child_chunks or not embeddings:
            logger.warning("No documents or embeddings provided to index.")
            return

        if len(child_chunks) != len(embeddings):
            raise ValueError(
                f"Count mismatch: received {len(child_chunks)} chunks and {len(embeddings)} vectors."
            )

        vector_dim = len(embeddings[0])

        # Validate or establish index dimension and model identity
        if self.index is None:
            self._initialize_index(vector_dim)
            self.model_name = model_name
        else:
            if self.model_name and model_name and self.model_name != model_name:
                raise IncompatibleEmbeddingModelError(
                    f"Index model '{self.model_name}' does not match incoming model '{model_name}'."
                )
            if self.dimension != vector_dim:
                raise ValueError(
                    f"Vector dimension {vector_dim} does not match index dimension {self.dimension}."
                )

        # Convert to float32 NumPy array and L2-normalize
        raw_vectors = np.array(embeddings, dtype=np.float32)
        normalized_vectors = self._normalize_vectors(raw_vectors)

        # Add to FAISS index
        self.index.add(normalized_vectors)

        # Store metadata associated with each vector index position
        self.child_documents.extend(child_chunks)

        # Store parent lookup mapping
        if parent_chunks:
            for p in parent_chunks:
                self.parent_documents[p["id"]] = p

        logger.info(
            "Indexed %d vectors | model=%s | dimension=%d | total_indexed=%d",
            len(embeddings),
            self.model_name,
            self.dimension,
            self.index.ntotal,
        )

    def similarity_search(
        self,
        query_embedding: List[float],
        query_model_name: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches the nearest child chunks for the given query vector.
        Enforces strict model name equality before calculating distances.
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Vector store is empty. Returning empty search results.")
            return []

        if self.model_name and query_model_name and self.model_name != query_model_name:
            raise IncompatibleEmbeddingModelError(
                f"Query model '{query_model_name}' incompatible with index model '{self.model_name}'."
            )

        # Prepare normalized query vector
        query_array = np.array([query_embedding], dtype=np.float32)
        normalized_query = self._normalize_vectors(query_array)

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(normalized_query, k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            child_record = self.child_documents[idx].copy()
            child_record["score"] = float(score)
            results.append(child_record)

        return results

    def retrieve_parent_chunks(
        self,
        query_embedding: List[float],
        query_model_name: str,
        top_k_parents: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top parent chunks by finding the most relevant child chunks
        and resolving their unique parent identifiers.
        """
        # Search a wider pool of children to aggregate unique parents
        child_pool_size = max(top_k_parents * 3, 5)
        top_children = self.similarity_search(
            query_embedding=query_embedding,
            query_model_name=query_model_name,
            top_k=child_pool_size,
        )

        selected_parent_ids = set()
        resolved_parents: List[Dict[str, Any]] = []

        for child in top_children:
            parent_id = child.get("parent_id")
            if not parent_id or parent_id in selected_parent_ids:
                continue

            parent_record = self.parent_documents.get(parent_id)
            if parent_record:
                selected_parent_ids.add(parent_id)
                enriched_parent = parent_record.copy()
                enriched_parent["relevance_score"] = child["score"]
                resolved_parents.append(enriched_parent)

            if len(resolved_parents) >= top_k_parents:
                break

        return resolved_parents

    def save(self, directory_path: str) -> None:
        """
        Persists the FAISS binary index and metadata JSON to the target directory.
        """
        import faiss

        target_dir = Path(directory_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        index_file = target_dir / "index.faiss"
        metadata_file = target_dir / "metadata.json"

        if self.index is not None:
            faiss.write_index(self.index, str(index_file))

        metadata_payload = {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "total_vectors": self.index.ntotal if self.index else 0,
            "child_documents": self.child_documents,
            "parent_documents": self.parent_documents,
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata_payload, f, ensure_ascii=False, indent=2)

        logger.info("Saved vector store to %s", str(target_dir))

    def load(self, directory_path: str) -> None:
        """
        Loads the FAISS binary index and metadata JSON from the target directory.
        """
        import faiss

        target_dir = Path(directory_path)
        index_file = target_dir / "index.faiss"
        metadata_file = target_dir / "metadata.json"

        if not index_file.exists() or not metadata_file.exists():
            raise FileNotFoundError(
                f"Missing vector store files in directory: {str(target_dir)}"
            )

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata_payload = json.load(f)

        self.model_name = metadata_payload.get("model_name", "")
        self.dimension = metadata_payload.get("dimension")
        self.child_documents = metadata_payload.get("child_documents", [])
        self.parent_documents = metadata_payload.get("parent_documents", {})

        self.index = faiss.read_index(str(index_file))
        logger.info(
            "Loaded vector store from %s | vectors=%d | model=%s",
            str(target_dir),
            self.index.ntotal,
            self.model_name,
        )


# ---------------------------------------------------------------------------
# Store factory (per-document FAISS indices)
# ---------------------------------------------------------------------------
# Content generation always targets a single document, never a cross-document
# search, so each document gets its own index directory instead of one shared
# index. This keeps deleting a document (drop its folder) and swapping this
# factory's internals for a future pgvector-backed one both straightforward,
# without changing BaseVectorStore or FAISSVectorStore themselves.

# In-process cache so repeated calls for the same document within one running
# server reuse the already-loaded store instead of hitting disk every time.
# Not shared across processes or safe for concurrent writers — acceptable at
# hackathon scale with a single backend process.
_store_cache: Dict[str, FAISSVectorStore] = {}


def _document_store_dir(document_id: str) -> Path:
    """Resolves the on-disk directory for one document's FAISS index."""
    return Path(settings.VECTOR_STORE_DIR) / document_id


def get_store(document_id: str) -> FAISSVectorStore:
    """
    Returns the FAISS store for a given document, creating an empty one if
    none exists yet on disk. Callers add_documents() and save_store() as needed;
    this function never writes to disk by itself.
    """
    if document_id in _store_cache:
        return _store_cache[document_id]

    store_dir = _document_store_dir(document_id)
    # Deliberately not pre-initialized with a dimension: FAISSVectorStore
    # only sets self.model_name on its first add_documents() call, which is
    # gated on self.index being None. Pre-creating the index here would skip
    # that branch and silently leave model_name empty forever, breaking the
    # incompatible-model check in similarity_search(). The dimension is still
    # enforced — embedding_service.py guarantees every vector already has
    # settings.EMBEDDING_DIMENSIONS before it reaches add_documents().
    store = FAISSVectorStore()

    if (store_dir / "index.faiss").exists() and (store_dir / "metadata.json").exists():
        store.load(str(store_dir))
    else:
        logger.info("No existing index for document_id=%s — starting a new one.", document_id)

    _store_cache[document_id] = store
    return store


def save_store(document_id: str, store: FAISSVectorStore) -> None:
    """Persists a document's store to its on-disk directory and refreshes the cache."""
    store.save(str(_document_store_dir(document_id)))
    _store_cache[document_id] = store


def clear_store_cache(document_id: Optional[str] = None) -> None:
    """Drops the in-process cache for one document, or all of them if omitted.
    Useful in tests, or after a document is deleted from disk."""
    if document_id is None:
        _store_cache.clear()
    else:
        _store_cache.pop(document_id, None)