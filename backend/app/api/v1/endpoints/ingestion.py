"""
ingestion.py

Purpose:
    FastAPI router providing asynchronous document ingestion endpoints:
    document upload with background processing, status polling, and document listing.

Input:
    - POST /upload: Multipart file upload (PDF, Markdown, or TXT) and optional document title.
    - GET /status/{document_id}: Document ID path parameter.
    - GET /documents: Optional user_id query parameter.

Output:
    JSON responses containing document metadata, status, chunk counts, or lists of document records.
"""

import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.document_record import DocumentRecord
from app.services.document_pipeline_service import (
    process_registered_document,
    register_document,
)
from app.services.document_repository import get_document_repository

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Response payload returned immediately upon document upload."""
    document_id: str
    status: str
    title: str
    source_filename: str
    message: str


class DocumentStatusResponse(BaseModel):
    """Response payload detailing the processing status of a document."""
    document_id: str
    status: str
    title: str
    source_filename: str
    total_parents: Optional[int] = None
    total_children: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document for background ingestion",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
) -> DocumentUploadResponse:
    """
    Receives a document, stores it, creates an initial database record,
    and schedules text extraction, chunking, embedding generation, and vector indexing
    as a background task.
    """
    filename = file.filename or "document.txt"
    extension = Path(filename).suffix.lower()

    if extension not in settings.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {extension}. Supported formats: {settings.SUPPORTED_EXTENSIONS}",
        )

    content_bytes = await file.read()
    size_mb = len(content_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB (received {size_mb:.1f}MB).",
        )

    resolved_title = title or Path(filename).stem.replace("_", " ").replace("-", " ").title()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    try:
        temp_file.write(content_bytes)
        temp_file.flush()
        temp_path = Path(temp_file.name)
    finally:
        temp_file.close()

    try:
        record = register_document(
            local_path=str(temp_path),
            title=resolved_title,
            user_id=user_id,
        )
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register document: {exc}",
        )

    background_tasks.add_task(
        process_registered_document,
        document_id=record.document_id,
        local_path=str(temp_path),
        title=resolved_title,
        cleanup_local=True,
    )

    return DocumentUploadResponse(
        document_id=record.document_id,
        status=record.status,
        title=record.title,
        source_filename=record.source_filename,
        message="Document uploaded and accepted for processing.",
    )


@router.get(
    "/status/{document_id}",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check document processing status",
)
def get_document_status(document_id: str) -> DocumentStatusResponse:
    """
    Retrieves the current indexing status and chunk counts for a given document.
    """
    repo = get_document_repository()
    try:
        record = repo.get_document(document_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    return DocumentStatusResponse(
        document_id=record.document_id,
        status=record.status,
        title=record.title,
        source_filename=record.source_filename,
        total_parents=record.total_parents,
        total_children=record.total_children,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/documents",
    response_model=List[DocumentRecord],
    status_code=status.HTTP_200_OK,
    summary="List all indexed documents",
)
def list_documents(user_id: Optional[str] = Query(None)) -> List[DocumentRecord]:
    """
    Returns the list of documents registered in the system, newest first.
    """
    repo = get_document_repository()
    return repo.list_documents(user_id=user_id)
