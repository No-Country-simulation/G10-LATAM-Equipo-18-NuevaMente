"""
ingestion.py

Purpose:
    FastAPI router handling document upload, validation, parsing,
    and structured layout-aware chunking for PDF, Markdown, and TXT files,
    including AI LLM Vision Parsing for complex PDFs.

Input:
    Uploaded file (multipart/form-data) via HTTP POST.

Output:
    JSON response containing cleaned text, suggested title, chunks, and metadata.
"""

import tempfile
from pathlib import Path
from typing import Tuple, Any
import anyio
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query

from app.core.config import settings
from app.services.ingester_service import IngesterService
from app.services.pdf_parser_service import PdfParserService
from app.services.oci_storage_service import OCIStorageService

router = APIRouter()
ingester_service = IngesterService()
pdf_parser_service = PdfParserService()
oci_storage_service = OCIStorageService()


def _save_and_process_document(
    content_bytes: bytes,
    extension: str,
    suggested_title: str,
    use_llm: bool,
) -> Tuple[Any, str]:
    """Saves content to a temporary file and parses it synchronously in a worker thread."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_file.write(content_bytes)
        temp_path = Path(temp_file.name)

    try:
        if use_llm and extension == ".pdf":
            parsed_llm = pdf_parser_service.parse_pdf_with_llm(str(temp_path))
            extracted_text = parsed_llm.get("markdown_text", "")
            engine_used = parsed_llm.get("engine", "Gemini 1.5 LLM Vision Parser")
            ingested_doc = ingester_service.process_text(extracted_text, title=suggested_title)
        else:
            ingested_doc = ingester_service.process_document(temp_path, title=suggested_title)
            engine_used = "PyMuPDF / Text Ingest Engine"
        return ingested_doc, engine_used
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _save_and_parse_pdf_llm(content_bytes: bytes) -> dict:
    """Saves PDF to a temporary file and parses it with LLM synchronously in a worker thread."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(content_bytes)
        temp_path = Path(temp_file.name)

    try:
        return pdf_parser_service.parse_pdf_with_llm(str(temp_path))
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.post("/parse-document", status_code=status.HTTP_200_OK)
@router.post("/parse-pdf", status_code=status.HTTP_200_OK)
async def parse_document(file: UploadFile = File(...), use_llm: bool = Query(False)):
    """
    Receives a technical document (PDF, Markdown, or TXT), validates size
    and format, extracts clean content, and returns structured metadata
    with Spanish keys for UI presentation. Supports optional use_llm=true for
    AI LLM Gemini Vision parsing.
    """
    filename = file.filename or "document.txt"
    extension = Path(filename).suffix.lower()

    if extension not in settings.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no compatible: {extension}. Formatos soportados: {settings.SUPPORTED_EXTENSIONS}",
        )

    try:
        content_bytes = await file.read()

        size_mb = len(content_bytes) / (1024 * 1024)
        if size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archivo demasiado pesado: {size_mb:.1f}MB. El límite permitido es de {settings.MAX_FILE_SIZE_MB}MB.",
            )

        suggested_title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

        ingested_doc, engine_used = await anyio.to_thread.run_sync(
            _save_and_process_document,
            content_bytes,
            extension,
            suggested_title,
            use_llm,
        )

        # Upload original document to OCI Object Storage Always Free bucket
        oci_doc_info = OCIStorageService().upload_document_source(
            bucket_name=settings.OCI_BUCKET_DOCS,
            object_name=filename,
            file_bytes=content_bytes,
            content_type="application/pdf" if extension == ".pdf" else "text/plain"
        )

        return {
            "status": "exito",
            "filename": filename,
            "titulo_sugerido": ingested_doc.title,
            "engine": engine_used,
            "total_chunks": len(ingested_doc.chunks),
            "texto_extraido": ingested_doc.raw_text,
            "chunks": [chunk.model_dump() for chunk in ingested_doc.chunks],
            "almacenamiento_oci": oci_doc_info
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento del documento: {str(error)}",
        )


@router.post("/parse-pdf-llm", status_code=status.HTTP_200_OK)
async def parse_pdf_llm(file: UploadFile = File(...)):
    """
    Endpoint especializado de Parsing PDF con IA LLM Gemini Vision:
    Convierte PDFs complejos (con tablas, diagramas y bloques de código)
    en Markdown estructurado preservando la jerarquía pedagógica.
    """
    filename = file.filename or "document.pdf"
    extension = Path(filename).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este endpoint requiere un archivo PDF (.pdf). Recibido: {extension}"
        )

    try:
        content_bytes = await file.read()
        suggested_title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

        parsed_result = await anyio.to_thread.run_sync(
            _save_and_parse_pdf_llm,
            content_bytes,
        )

        return {
            "status": "exito",
            "filename": filename,
            "titulo_sugerido": suggested_title,
            "engine": parsed_result.get("engine", "Gemini 1.5 LLM Vision Parser"),
            "texto_extraido": parsed_result.get("markdown_text", ""),
            "total_paginas": parsed_result.get("page_count", 1),
            "metadatos_ia": {
                "tablas_detectadas": parsed_result.get("detected_tables", 0),
                "conceptos_clave": parsed_result.get("key_concepts", []),
                "resumen": parsed_result.get("summary", "")
            }
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el parsing IA LLM del PDF: {str(error)}"
        )
