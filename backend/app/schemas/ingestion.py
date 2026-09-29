"""
ingestion.py

Purpose:
    Typed data contracts for the document ingestion and chunking layer.
    Pure data shapes only — the parent/child RAG formatting logic that
    used to live here moved to IngesterService.build_rag_chunks(), since
    a schema should describe data, not perform processing. RAG-stage shapes
    (Parent/Child chunks, embeddings) live in schemas/rag_chunks.py instead,
    since those belong to a later pipeline stage, not to raw ingestion.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class IngestionOptions(BaseModel):
    """Optional settings for how a document is processed."""
    pdf_extraction_strategy: str = "raw"


class DocumentChunk(BaseModel):
    """Represents a segment of a source document."""
    chunk_id: str
    document_id: str
    text: str
    section_title: Optional[str] = None
    heading_level: Optional[int] = None
    page_number: Optional[int] = None


class IngestedDocument(BaseModel):
    """Represents a processed document with text and chunks."""
    document_id: str
    title: str
    source_filename: str
    raw_text: str
    chunks: List[DocumentChunk] = Field(default_factory=list)