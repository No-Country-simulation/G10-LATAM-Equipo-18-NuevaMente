"""
document_record.py

Purpose:
    Typed data contract for a row in the `documents` table: the metadata
    NuevaMente tracks about an uploaded document (title, storage location,
    processing status) — separate from its content (schemas/ingestion.py)
    and from its RAG chunks (schemas/rag_chunks.py).

Input:
    Constructed by DocumentRepository implementations from a database row.

Output:
    Consumed by document_pipeline_service.py and, eventually, by the
    document-listing endpoint.
"""

from typing import Optional
from pydantic import BaseModel

# Valid values for DocumentRecord.status.
STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"


class DocumentRecord(BaseModel):
    """A row in the `documents` table."""
    document_id: str
    user_id: Optional[str] = None
    title: str
    source_filename: str
    object_key: str
    status: str = STATUS_PROCESSING
    total_parents: Optional[int] = None
    total_children: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None