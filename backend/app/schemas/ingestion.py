"""
ingestion.py

Purpose:
    Typed data contracts for the document ingestion and chunking layer.
    Pure data shapes only — the parent/child RAG formatting logic that
    used to live here moved to IngesterService.build_rag_chunks(), since
    a schema should describe data, not perform processing. RAG-stage shapes
    (Parent/Child chunks, embeddings) live in schemas/rag_chunks.py instead,
    since those belong to a later pipeline stage, not to raw ingestion.

    Also defines the options that control text cleaning and noise filtering
    (per request, overriding the defaults in settings) and the report that
    describes which sections the noise filter discarded and why.

Input:
    Constructed by IngesterService and NoiseFilter, or by a caller that
    passes IngestionOptions to IngesterService.

Output:
    Validated models consumed by IngesterService, NoiseFilter and the
    document pipeline.
"""

from typing import List, Literal, Optional, Tuple, get_args
from pydantic import BaseModel, Field

# Categories of non-technical content the noise filter can discard.
NoiseCategory = Literal[
    "legal",
    "revision_history",
    "index_lists",
    "near_empty",
    "normative_appendix",
]
NOISE_CATEGORIES: Tuple[str, ...] = get_args(NoiseCategory)


class IngestionOptions(BaseModel):
    """Optional settings for how a document is processed. A None value
    means "use the default from settings"."""
    pdf_extraction_strategy: str = "raw"
    clean_text: Optional[bool] = None
    filter_noise: Optional[bool] = None
    # None applies every category; a list restricts the filter to those.
    noise_categories: Optional[List[NoiseCategory]] = None
    # When True the filter only reports what it would discard, and discards nothing.
    noise_dry_run: bool = False


class NoiseReportEntry(BaseModel):
    """One section evaluated as noise by the filter."""
    category: NoiseCategory
    reason: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    char_count: int
    preview: str = ""
    # False for entries reported in dry-run mode or when the filter was skipped.
    discarded: bool = True


class NoiseReport(BaseModel):
    """Summary of one noise filter run over a document."""
    dry_run: bool = False
    total_chars: int = 0
    discarded_chars: int = 0
    discard_ratio: float = 0.0
    # Set when the filter found noise but did not apply it (e.g. ratio too high).
    skipped_reason: Optional[str] = None
    entries: List[NoiseReportEntry] = Field(default_factory=list)


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
    # Present only when the noise filter ran on this document.
    noise_report: Optional[NoiseReport] = None