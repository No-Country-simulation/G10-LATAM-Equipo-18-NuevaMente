"""
document_pipeline_service.py

Purpose:
    Orchestrates everything that must happen to a newly uploaded document
    before content can be generated from it: uploads the original file,
    records its metadata, ingests and chunks it, generates embeddings, and
    indexes it. Ties together document_storage_service, document_repository,
    ingester_service, embedding_service and vector_store_service — none of
    which know about each other or about this orchestration.

    One document_id is generated here and threaded through all of them, so
    the uploaded file's object_key, its row in the `documents` table, and
    its FAISS index directory all refer to the same document.

    Progress is reported through an optional callback, so a UI can show what
    is happening (including waits and provider switches) without this module
    knowing anything about the UI.

Input:
    - local_path (str): path to the already-received file on local disk
      (an endpoint is expected to have written it there from the upload).
    - title (str, optional): defaults to the filename without extension.
    - user_id (str, optional): None until login exists.
    - on_progress (Callable[[dict], None], optional): receives events with keys
      "stage" and "message" (Spanish, ready to display), plus optionally
      "current", "total", "wait_seconds", "provider".
      Stages: uploading, ingesting, embedding, waiting, retrying,
      switching_provider, indexing, ready, failed.
      The callback runs in the calling thread; its errors are ignored.

Output:
    - DocumentRecord: the final row from the `documents` table, with
      status "ready" (indexed successfully) or "failed" (with error_message
      set) — never partially updated, since a failure marks the document
      failed rather than leaving it stuck at "processing".
"""

import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from app.schemas.document_record import DocumentRecord
from app.services.document_storage_service import get_document_storage
from app.services.document_repository import get_document_repository
from app.services.ingester_service import IngesterService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import get_store, save_store

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[Dict[str, Any]], None]


def _emit(on_progress: Optional[ProgressCallback], stage: str, message: str, **extra: Any) -> None:
    """Sends a progress event to the callback; a failing callback never breaks the pipeline."""
    if on_progress is None:
        return
    try:
        on_progress({"stage": stage, "message": message, **extra})
    except Exception as exc:
        logger.warning("Progress callback raised an error and was ignored: %s", exc)


def process_and_index_document(
    local_path: str,
    title: Optional[str] = None,
    user_id: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> DocumentRecord:
    """
    Runs the full pipeline for one document and returns its final record.
    Raises if the upload or the initial metadata row can't be created —
    there's nothing to mark failed yet at that point. Once the document row
    exists, any later failure is caught and recorded via mark_failed()
    instead of propagating silently. Every failure also emits a "failed"
    progress event before the exception is raised.
    """
    document_id = str(uuid.uuid4())
    path = Path(local_path)
    resolved_title = title or path.stem

    storage = get_document_storage()
    repo = get_document_repository()

    try:
        logger.info("Uploading original file for document_id=%s", document_id)
        _emit(on_progress, "uploading", "Subiendo el archivo original…")
        object_key = storage.upload_document(
            local_path=str(path),
            user_id=user_id,
            document_id=document_id,
        )

        repo.create_document(
            document_id=document_id,
            title=resolved_title,
            source_filename=path.name,
            object_key=object_key,
            user_id=user_id,
        )
    except Exception as exc:
        _emit(on_progress, "failed", f"No se pudo registrar el documento: {exc}")
        raise

    try:
        _ingest_embed_and_index(path, resolved_title, document_id, repo, on_progress)
    except Exception as exc:
        logger.error("Pipeline failed for document_id=%s: %s", document_id, exc)
        repo.mark_failed(document_id, error_message=str(exc))
        _emit(on_progress, "failed", f"Falló el procesamiento del documento: {exc}")
        raise

    return repo.get_document(document_id)


def _ingest_embed_and_index(
    path: Path,
    title: str,
    document_id: str,
    repo,
    on_progress: Optional[ProgressCallback] = None,
) -> None:
    """Ingestion + embedding + indexing, kept separate from
    process_and_index_document() so the try/except there only wraps the
    steps that can legitimately fail mid-way — upload and the initial
    metadata row either succeed outright or raise before there's anything
    to mark failed."""
    _emit(on_progress, "ingesting", "Leyendo y dividiendo el documento en fragmentos…")
    ingester = IngesterService()
    document = ingester.process_document(path, title=title, document_id=document_id)
    rag_payload = ingester.build_rag_chunks(document)

    child_chunks = rag_payload["child_chunks"]
    parent_chunks = rag_payload["parent_chunks"]

    # The embedding service reports its own progress events (batches, waits,
    # retries, provider switches) through the same callback.
    embedding_svc = EmbeddingService()
    child_texts = [chunk["content"] for chunk in child_chunks]
    embeddings = embedding_svc.embed_batch(child_texts, on_progress=on_progress)

    _emit(on_progress, "indexing", "Guardando el índice de búsqueda…")
    vector_store = get_store(document_id)
    vector_store.add_documents(
        child_chunks=child_chunks,
        embeddings=embeddings,
        parent_chunks=parent_chunks,
        model_name=embedding_svc.model_name,
    )
    save_store(document_id, vector_store)

    repo.mark_ready(
        document_id,
        total_parents=rag_payload["total_parents"],
        total_children=rag_payload["total_children"],
    )
    logger.info(
        "document_id=%s ready — %d parents, %d children indexed",
        document_id, rag_payload["total_parents"], rag_payload["total_children"],
    )
    _emit(
        on_progress,
        "ready",
        f"Documento listo: {rag_payload['total_parents']} secciones y "
        f"{rag_payload['total_children']} fragmentos indexados.",
    )