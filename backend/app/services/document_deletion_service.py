"""
document_deletion_service.py

Purpose:
    Deletes one indexed document from every layer that holds it: the original
    file in object storage, the per-document FAISS index on disk, and the
    metadata row in the `documents` table.

    The deletion order is fixed so that a failure never reports a deletion
    that did not happen, and always leaves the document in a state a retry
    can finish: storage goes first because it is the only irreversible step
    and it is idempotent (an object that is already gone counts as deleted),
    while the index and the metadata row are only touched afterwards.

Input:
    - document_id: the document to delete.
    - requester_id: the owner allowed to delete it. None skips the ownership
      check and is reserved for maintenance scripts.

Output:
    - A dict describing what was deleted.
    - HTTPException when the document cannot be deleted: 404 when it does
      not exist or belongs to another user, 409 while it is still being
      processed, 502 when object storage failed, 500 when the local index
      could not be removed.
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.core.security import get_db
from app.schemas.document_record import STATUS_PROCESSING
from app.services.document_repository import get_document_repository
from app.services.document_storage_service import get_document_storage
from app.services.vector_store_service import delete_store

logger = logging.getLogger("nuevamente.documents")


class DocumentDeletionService:
    """Removes a document and all of its derived artifacts."""

    def delete_document(
        self,
        document_id: str,
        requester_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deletes one document and returns a summary of what was removed."""
        repo = get_document_repository()
        record = repo.get_document(document_id)

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' was not found.",
            )

        # A document owned by someone else is reported as missing, never as
        # forbidden, so the endpoint cannot be used to probe for foreign ids.
        if requester_id is not None and record.user_id and str(record.user_id) != str(requester_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' was not found.",
            )

        # The ingestion pipeline runs in a background thread and writes the
        # index at the end of its run, so deleting now would let it recreate
        # the index directory afterwards.
        if record.status == STATUS_PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Document '{document_id}' is still being processed. "
                    "Wait until it finishes before deleting it."
                ),
            )

        # 1. Object storage first. delete_document() treats an already-missing
        #    object as deleted and raises on every other failure.
        try:
            get_document_storage().delete_document(record.object_key)
        except Exception as exc:
            logger.error(
                "Failed to delete the stored file for document_id=%s (object_key=%s): %s",
                document_id,
                record.object_key,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "No se pudo eliminar el archivo del almacenamiento de objetos. "
                    "El documento no fue eliminado; inténtalo de nuevo."
                ),
            )

        # 2. Vector index on disk plus its in-process cache entry.
        try:
            vector_store_removed = delete_store(document_id)
        except OSError as exc:
            logger.error("Failed to remove the vector index of document_id=%s: %s", document_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "No se pudo eliminar el índice vectorial del documento. "
                    "El documento no fue eliminado; inténtalo de nuevo."
                ),
            )

        # 3. Metadata row, which is what the documents list reads from.
        row_deleted = repo.delete_document(document_id)

        self._log_audit(requester_id or record.user_id or "system", document_id, record.title)

        return {
            "status": "exito",
            "mensaje": f"Documento '{record.title}' eliminado definitivamente.",
            "document_id": document_id,
            "object_key": record.object_key,
            "vector_store_removed": vector_store_removed,
            "row_deleted": row_deleted,
        }

    def _log_audit(self, user_id: str, document_id: str, title: str) -> None:
        """Records the deletion in the audit log; never fails the deletion."""
        try:
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO audit_log (id, user_id, action, resource_id, details, timestamp)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        f"audit-{uuid.uuid4().hex[:12]}",
                        user_id,
                        "delete_document",
                        document_id,
                        f"Deleted document '{title}'",
                        time.time(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Audit log entry for document deletion failed: %s", exc)


def get_document_deletion_service() -> DocumentDeletionService:
    """Factory for the document deletion service."""
    return DocumentDeletionService()
