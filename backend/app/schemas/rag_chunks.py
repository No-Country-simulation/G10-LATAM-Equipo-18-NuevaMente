"""
rag_chunks.py

Purpose:
    Typed data contracts for the Parent/Child hierarchical chunks that flow
    through the RAG pipeline: built by IngesterService.build_rag_chunks(),
    indexed by vector_store_service, read back by retrieval_service, and
    scored by reranker_service. Kept separate from schemas/ingestion.py,
    which only describes the raw ingested document — these describe the
    RAG-stage data derived from it, not the ingestion output itself.

    Pure data shapes only, same rule as ingestion.py: no processing logic.

Input:
    Constructed by IngesterService.build_rag_chunks() from an
    IngestedDocument's chunks.

Output:
    Validated once at creation time, then passed downstream as plain dicts
    (via .model_dump()) — vector_store_service, retrieval_service and
    reranker_service already operate on dicts (dict subscripting, .copy(),
    .get()), so this validates the shape at its source without requiring
    every consumer to be rewritten around a Pydantic model.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ParentChunkMetadata(BaseModel):
    """Metadata attached to a Parent chunk (a full section)."""
    source_title: str
    section_index: int
    page_number: Optional[int] = None
    heading_level: Optional[int] = None
    # Populated only when settings.USE_KEYBERT_CONCEPTS is enabled; empty otherwise.
    key_concepts: List[str] = Field(default_factory=list)


class ChildChunkMetadata(BaseModel):
    """Metadata attached to a Child chunk (a smaller piece of a Parent)."""
    parent_id: str
    source: str


class ParentChunk(BaseModel):
    """A full section, used as generation context once a Child chunk it
    contains is found relevant."""
    id: str
    title: str
    breadcrumb: str
    content: str
    metadata: ParentChunkMetadata
    # Set by retrieval_service after reranking; absent before that stage.
    relevance_score: Optional[float] = None


class ChildChunk(BaseModel):
    """A smaller piece of a Parent chunk, the unit actually embedded and
    indexed for similarity search."""
    id: str
    parent_id: str
    breadcrumb: str
    content: str
    metadata: ChildChunkMetadata
    # Set by FAISSVectorStore.similarity_search; absent before a search runs.
    score: Optional[float] = None