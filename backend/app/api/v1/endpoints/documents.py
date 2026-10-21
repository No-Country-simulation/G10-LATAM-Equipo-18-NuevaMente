"""
documents.py

Purpose:
    HTTP surface for the real RAG pipeline: ingesting one document (upload or
    pasted text) into storage + vector index, listing the documents a user
    owns, and generating educational content from an already-indexed
    document. This is the HTTP equivalent of what the Gradio test UI did
    in-process, replacing the old stateless /adapt-content endpoint.

Input:
    - POST /documents: multipart with either a `file` upload or `text`
      (pasted content), plus optional `title`, `use_ai_vision` and `user_id`.
      Query `stream=true` (default) returns live progress as Server-Sent
      Events.
    - POST /documents/{document_id}/adapt: JSON generation parameters
      (profile, format, niche, language, quantity) with Spanish aliases.
    - GET /documents and GET /documents/{document_id}.
    - DELETE /documents/{document_id}: permanently removes one document from
      object storage, from the vector index and from the documents table.

Output:
    - SSE stream of progress events while ingesting, ending with a "done"
      event (or "failed"); a plain JSON document record when `stream=false`.
    - AdaptationResponse for content generation (same contract the frontend
      already renders for every output format).
    - DocumentRecord list/single record for the documents pages.
    - A deletion summary for DELETE /documents/{document_id}.
"""

import json
import logging
import queue
import tempfile
import threading
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

import anyio
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.v1.dependencies import get_current_user
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.schemas.adaptation import AdaptationRequest, AdaptationResponse
from app.schemas.document_record import DocumentRecord
from app.services.document_pipeline_service import (
    process_registered_document,
    register_document,
)
from app.services.document_deletion_service import get_document_deletion_service
from app.services.document_repository import get_document_repository
from app.services.langgraph_orchestrator import LangGraphOrchestrator
from app.services.retrieval_service import retrieve_context
from app.services.vector_store_service import get_store

logger = logging.getLogger(__name__)

router = APIRouter()

langgraph_orchestrator = LangGraphOrchestrator()


class DocumentAdaptRequest(BaseModel):
    """Generation parameters for one already-indexed document."""
    model_config = ConfigDict(populate_by_name=True)

    recipient_profile: str = Field(..., alias="perfil_destinatario")
    output_format: str = Field(..., alias="formato_salida")
    niche: str = Field(default="general", alias="nicho_sector")
    detail_level: str = Field(default="didactic", alias="nivel_detalle")
    quantity_level: Optional[str] = Field(default="Estandar", alias="nivel_cantidad")
    target_quantity: Optional[int] = Field(default=None, alias="cantidad_objetivo")
    quantity: Optional[int] = Field(default=5, alias="cantidad_generar")
    language: Optional[str] = Field(default=None, alias="idioma_salida")
    additional_instructions: Optional[str] = Field(default=None, alias="instrucciones_adicionales")
    force_regenerate: Optional[bool] = Field(default=True, alias="forzar_regenerar")


def _format_sse(payload: Dict[str, Any]) -> str:
    """Serializes one progress event as a Server-Sent Events frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# Spanish fallback messages for each generation step. The frontend localizes
# the step labels itself using the stage key, so these are only a resilience
# fallback for clients that render the raw message.
_GENERATION_STAGE_MESSAGES: Dict[str, str] = {
    "retrieval": "Recuperando los fragmentos más relevantes (RAG)…",
    "planner": "Planificando cobertura y tópicos pedagógicos…",
    "writer": "Redactando el contenido educativo…",
    "deduplicator": "Eliminando ítems duplicados…",
    "grounding_verifier": "Verificando el anclaje a las fuentes…",
    "critic": "Auditando la calidad pedagógica…",
    "refiner": "Completando ítems faltantes…",
    "formatter": "Formateando y guardando el contenido…",
}


def _save_upload_to_temp(content_bytes: bytes, suffix: str) -> str:
    """Writes uploaded/pasted bytes to a temporary file and returns its path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content_bytes)
        return temp_file.name


def _remove_quietly(local_path: str) -> None:
    """Best-effort removal of the temporary file, never raising on failure."""
    try:
        Path(local_path).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to remove temporary file %s: %s", local_path, exc)


def _ingest(
    local_path: str,
    title: str,
    user_id: Optional[str],
    use_ai_vision: bool,
    on_progress,
    source_filename: Optional[str] = None,
) -> DocumentRecord:
    """Registers the file and runs the full ingest + embed + index pipeline."""
    record = register_document(
        local_path=local_path,
        title=title,
        user_id=user_id,
        on_progress=on_progress,
        source_filename=source_filename,
    )
    return process_registered_document(
        document_id=record.document_id,
        local_path=local_path,
        title=title,
        on_progress=on_progress,
        cleanup_local=False,
        use_ai_vision=use_ai_vision,
    )


@router.post("/documents")
async def create_document(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    use_ai_vision: bool = Form(False),
    user_id: Optional[str] = Form(None),
    stream: bool = Query(True, description="Stream progress as Server-Sent Events"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Ingests a document and indexes it for retrieval.

    Accepts either an uploaded file or pasted plain text (both go through the
    same pipeline). With stream=true it reports live progress; with
    stream=false it returns the final document record once indexing finishes.
    """
    pasted_text = (text or "").strip()

    if file is None and not pasted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a file or pasted text to ingest.",
        )

    if file is not None:
        filename = file.filename or "document.txt"
        suffix = Path(filename).suffix.lower()
        if suffix not in settings.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {suffix}. Supported: {settings.SUPPORTED_EXTENSIONS}",
            )
        content_bytes = await file.read()
    else:
        suffix = ".txt"
        filename = "texto_pegado.txt"
        content_bytes = pasted_text.encode("utf-8")

    size_mb = len(content_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {size_mb:.1f}MB. Limit is {settings.MAX_FILE_SIZE_MB}MB.",
        )

    resolved_title = (title or Path(filename).stem.replace("_", " ").replace("-", " ")).strip()
    # `filename` may carry client-side directory separators; keep only the
    # basename so the documents table stores the real uploaded name
    # ("manual_vcn.pdf") instead of the internal temporary file name.
    source_filename = Path(filename).name
    local_path = _save_upload_to_temp(content_bytes, suffix)
    derived_user_id = current_user["id"] if current_user else user_id

    if stream:
        return StreamingResponse(
            _ingest_event_stream(local_path, resolved_title, derived_user_id, use_ai_vision, source_filename),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        record = await anyio.to_thread.run_sync(
            lambda: _ingest(local_path, resolved_title, derived_user_id, use_ai_vision, None, source_filename)
        )
    finally:
        _remove_quietly(local_path)
    return record


def _ingest_event_stream(
    local_path: str,
    title: str,
    user_id: Optional[str],
    use_ai_vision: bool,
    source_filename: Optional[str] = None,
) -> Generator[str, None, None]:
    """Runs ingestion in a worker thread and yields each progress event as SSE."""
    events: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
    outcome: Dict[str, Any] = {}

    def worker() -> None:
        try:
            outcome["record"] = _ingest(
                local_path, title, user_id, use_ai_vision, events.put, source_filename
            )
        except Exception as exc:  # surfaced to the client as a failed event
            outcome["error"] = str(exc)
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    yield _format_sse({"stage": "uploading", "message": "Preparando la ingesta…"})
    while True:
        event = events.get()
        if event is None:
            break
        yield _format_sse(event)

    _remove_quietly(local_path)

    if "error" in outcome:
        yield _format_sse({"stage": "failed", "message": outcome["error"]})
        return

    record: DocumentRecord = outcome["record"]
    yield _format_sse({
        "stage": "done",
        "document_id": record.document_id,
        "status": record.status,
        "title": record.title,
        "total_parents": record.total_parents,
        "total_children": record.total_children,
        "storage_backend": record.storage_backend,
    })


@router.get("/documents", response_model=List[DocumentRecord])
async def list_documents(
    user_id: Optional[str] = Query(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """Lists indexed documents, newest first, filtered by owner."""
    owner_id = current_user["id"] if current_user else user_id
    return get_document_repository().list_documents(user_id=owner_id)


@router.get("/documents/{document_id}", response_model=DocumentRecord)
async def get_document(
    document_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """Returns one document's metadata record."""
    record = get_document_repository().get_document(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found.",
        )
    if current_user and record.user_id and str(record.user_id) != str(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para acceder a este documento.",
        )
    return record


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Permanently deletes one document and everything derived from it.

    Removes the original file from object storage, the FAISS index from disk
    and the metadata row from the documents table. The deletion is refused
    with 409 while the document is still being processed, and a storage or
    index failure leaves the document untouched so the user can retry.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debe iniciar sesión para eliminar un documento.",
        )

    return get_document_deletion_service().delete_document(
        document_id=document_id,
        requester_id=current_user["id"],
    )


def _build_adaptation_request(
    record: DocumentRecord,
    request: "DocumentAdaptRequest",
    top_passages: List[Dict[str, Any]],
    user_id: Optional[str],
) -> AdaptationRequest:
    """Assembles the internal AdaptationRequest from the HTTP payload + passages."""
    return AdaptationRequest(
        title=record.title,
        content="\n\n".join(passage.get("content", "") for passage in top_passages),
        recipient_profile=request.recipient_profile,
        output_format=request.output_format,
        niche=request.niche,
        detail_level=request.detail_level,
        quantity_level=request.quantity_level,
        target_quantity=request.target_quantity,
        quantity=request.quantity,
        language=request.language,
        additional_instructions=request.additional_instructions,
        force_regenerate=request.force_regenerate,
        user_id=user_id or record.user_id,
    )


async def _adapt_event_stream(
    document_id: str,
    record: DocumentRecord,
    request: "DocumentAdaptRequest",
    query: str,
    store: Any,
    user_id: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Streams retrieval plus one event per LangGraph node as SSE.

    Emits `{"stage": <name>}` while working and a final
    `{"stage": "done", "response": <AdaptationResponse>}` frame, mirroring the
    ingestion stream contract so the frontend can reuse one consumer.
    """
    yield _format_sse({"stage": "retrieval", "message": _GENERATION_STAGE_MESSAGES["retrieval"]})

    try:
        top_passages = await anyio.to_thread.run_sync(
            lambda: retrieve_context(
                document_id=document_id, query=query, top_k=settings.MAX_TOP_K_CHUNKS
            )
        )
    except Exception as exc:  # reported to the client as a failed event
        logger.exception("Error retrieving context for document_id=%s", document_id)
        yield _format_sse({"stage": "failed", "message": f"Retrieval error: {exc}"})
        return

    if not top_passages:
        yield _format_sse(
            {"stage": "failed", "message": "No relevant passages were found for this document."}
        )
        return

    all_parent_chunks = list(store.parent_documents.values())
    adaptation_request = _build_adaptation_request(record, request, top_passages, user_id)

    try:
        async for event in langgraph_orchestrator.iter_pipeline(
            request=adaptation_request,
            top_passages=top_passages,
            key_concepts=[],
            prerequisites=[],
            all_parent_chunks=all_parent_chunks,
            document_id=document_id,
        ):
            stage = event.get("stage")
            if stage == "done":
                response: AdaptationResponse = event["response"]
                yield _format_sse({"stage": "done", "response": response.model_dump(by_alias=True)})
            else:
                yield _format_sse(
                    {"stage": stage, "message": _GENERATION_STAGE_MESSAGES.get(stage, "")}
                )
    except Exception as error:
        logger.exception("Error generating content for document_id=%s", document_id)
        yield _format_sse({"stage": "failed", "message": f"Content generation error: {error}"})


@router.post("/documents/{document_id}/adapt", response_model=AdaptationResponse)
async def adapt_document(
    document_id: str,
    request: DocumentAdaptRequest,
    user_id: Optional[str] = Query(None),
    stream: bool = Query(False, description="Stream generation progress as Server-Sent Events"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Generates educational content from an already-indexed document.

    Retrieval runs against the document's FAISS store; generation runs the
    multi-agent pipeline. With `stream=true` it reports live progress (one
    event per graph node) and ends with the full response; with `stream=false`
    it returns the response directly.
    """
    repo = get_document_repository()
    record = repo.get_document(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found.",
        )
    if current_user and record.user_id and str(record.user_id) != str(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para acceder a este documento.",
        )
    if record.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document status is '{record.status}'. It must be 'ready' to generate content.",
        )

    store = get_store(document_id)
    if store is None or not store.child_documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The document has no indexed vector store.",
        )

    query = " ".join(
        part for part in [record.title, request.recipient_profile, request.output_format, request.niche] if part
    )

    if stream:
        return StreamingResponse(
            _adapt_event_stream(document_id, record, request, query, store, current_user["id"] if current_user else user_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    top_passages = await anyio.to_thread.run_sync(
        lambda: retrieve_context(document_id=document_id, query=query, top_k=settings.MAX_TOP_K_CHUNKS)
    )
    if not top_passages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No relevant passages were found for this document.",
        )

    all_parent_chunks = list(store.parent_documents.values())
    adaptation_request = _build_adaptation_request(record, request, top_passages, current_user["id"] if current_user else user_id)

    try:
        return await langgraph_orchestrator.run_pipeline(
            request=adaptation_request,
            top_passages=top_passages,
            key_concepts=[],
            prerequisites=[],
            all_parent_chunks=all_parent_chunks,
            document_id=document_id,
        )
    except Exception as error:
        logger.exception("Error generating content for document_id=%s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation error: {str(error)}",
        )
