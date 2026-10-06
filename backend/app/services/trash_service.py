"""
trash_service.py

Purpose:
    Backend service for user-isolated trash management, soft deletion,
    permanent deletion with OCI storage cleanup, fault tolerance,
    audit logging, and automatic retention purge.
"""

import uuid
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import get_db
from app.services.oci_storage_service import OCIStorageService

logger = logging.getLogger("nuevamente.trash")
_PURGE_LOCK = threading.Lock()


class TrashService:
    def __init__(self, oci_service: Optional[OCIStorageService] = None):
        self.oci_service = oci_service or OCIStorageService()

    def _now_utc(self, custom_now: Optional[datetime] = None) -> datetime:
        return custom_now or datetime.now(timezone.utc)

    def log_audit(self, user_id: str, action: str, resource_id: Optional[str] = None, details: Optional[str] = None) -> None:
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log (id, user_id, action, resource_id, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"audit-{uuid.uuid4().hex[:12]}", user_id, action, resource_id, details, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging audit action '{action}' for user '{user_id}': {e}")

    def move_to_trash(self, user_id: str, content_id: str, custom_now: Optional[datetime] = None) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "codigo": "RECURSO_NO_ENCONTRADO",
                    "mensaje": f"El contenido '{content_id}' no fue encontrado."
                }
            )

        content_data = dict(row)
        if content_data.get("user_id") != user_id:
            conn.close()
            # Security Rule: Return 404 (NEVER 403) for non-owned resources to prevent info leakage
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "codigo": "RECURSO_NO_ENCONTRADO",
                    "mensaje": f"El contenido '{content_id}' no fue encontrado."
                }
            )

        now = self._now_utc(custom_now)
        retention_days = getattr(settings, "TRASH_RETENTION_DAYS", 15)
        purge_at = now + timedelta(days=retention_days)

        now_iso = now.isoformat()
        purge_iso = purge_at.isoformat()

        cursor.execute("""
            UPDATE contenidos 
            SET deleted_at = ?, purge_at = ?, deleted_by = ?
            WHERE id = ?
        """, (now_iso, purge_iso, user_id, content_id))
        conn.commit()

        cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
        updated_row = cursor.fetchone()
        conn.close()

        self.log_audit(user_id, "move_to_trash", resource_id=content_id, details=f"Purge scheduled at {purge_iso}")
        return dict(updated_row)

    def list_trash(self, user_id: str, custom_now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        # Run lazy backup purge first
        self.lazy_purge_expired(custom_now)

        now_iso = self._now_utc(custom_now).isoformat()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM contenidos 
            WHERE user_id = ? AND deleted_at IS NOT NULL AND (purge_at IS NULL OR purge_at > ?)
            ORDER BY purge_at ASC
        """, (user_id, now_iso))
        rows = cursor.fetchall()
        conn.close()

        return [dict(r) for r in rows]

    def restore_content(self, user_id: str, content_id: str) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "codigo": "RECURSO_NO_ENCONTRADO",
                    "mensaje": f"El contenido '{content_id}' no fue encontrado."
                }
            )

        content_data = dict(row)
        if content_data.get("user_id") != user_id:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "codigo": "RECURSO_NO_ENCONTRADO",
                    "mensaje": f"El contenido '{content_id}' no fue encontrado."
                }
            )

        cursor.execute("""
            UPDATE contenidos 
            SET deleted_at = NULL, purge_at = NULL, deleted_by = NULL, purge_failed = 0
            WHERE id = ?
        """, (content_id,))
        conn.commit()

        cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
        updated_row = cursor.fetchone()
        conn.close()

        self.log_audit(user_id, "restore", resource_id=content_id, details="Restored to library")
        return dict(updated_row)

    def delete_permanently(
        self, 
        user_id: str, 
        content_id: str, 
        is_auto_purge: bool = False,
        custom_now: Optional[datetime] = None
    ) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contenidos WHERE id = ?", (content_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            if is_auto_purge:
                return True
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "codigo": "RECURSO_NO_ENCONTRADO",
                    "mensaje": f"El contenido '{content_id}' no fue encontrado."
                }
            )

        content_data = dict(row)
        owner_id = content_data.get("user_id")
        if not is_auto_purge and owner_id != user_id:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "codigo": "RECURSO_NO_ENCONTRADO",
                    "mensaje": f"El contenido '{content_id}' no fue encontrado."
                }
            )

        # 1. Attempt OCI Storage Deletion (under usuarios/{user_id}/...)
        src_key = content_data.get("object_key_source")
        json_key = content_data.get("object_key_json")
        oci_success = True

        for key in [src_key, json_key]:
            if key:
                try:
                    self.oci_service.delete_file(key)
                except Exception as e:
                    logger.error(f"OCI Deletion failed for object_key '{key}': {e}")
                    oci_success = False

        if not oci_success:
            # Fault tolerance: Mark purge_failed = 1 and DO NOT delete DB record
            cursor.execute("UPDATE contenidos SET purge_failed = 1 WHERE id = ?", (content_id,))
            conn.commit()
            conn.close()

            if not is_auto_purge:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "status": "error",
                        "codigo": "OCI_PURGE_FAILED",
                        "mensaje": "Error al eliminar los archivos en OCI Object Storage. Se ha marcado para reintento automático."
                    }
                )
            return False

        # 2. OCI deletion succeeded -> Delete DB Record
        cursor.execute("DELETE FROM contenidos WHERE id = ?", (content_id,))
        conn.commit()
        conn.close()

        action = "auto_purge" if is_auto_purge else "delete_permanently"
        self.log_audit(user_id, action, resource_id=content_id, details="Permanent deletion complete")
        return True

    def empty_trash(self, user_id: str, custom_now: Optional[datetime] = None) -> int:
        trashed_items = self.list_trash(user_id, custom_now)
        count = 0
        for item in trashed_items:
            try:
                if self.delete_permanently(user_id, item["id"], is_auto_purge=False, custom_now=custom_now):
                    count += 1
            except HTTPException:
                pass

        self.log_audit(user_id, "empty_trash", details=f"Emptied {count} items from trash")
        return count

    def lazy_purge_expired(self, custom_now: Optional[datetime] = None) -> None:
        now_iso = self._now_utc(custom_now).isoformat()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id FROM contenidos 
            WHERE deleted_at IS NOT NULL AND purge_at IS NOT NULL AND purge_at <= ?
        """, (now_iso,))
        expired_rows = cursor.fetchall()
        conn.close()

        for r in expired_rows:
            try:
                self.delete_permanently(r["user_id"], r["id"], is_auto_purge=True, custom_now=custom_now)
            except Exception as e:
                logger.error(f"Lazy purge error for item '{r['id']}': {e}")

    def auto_purge(self, batch_size: int = 50, custom_now: Optional[datetime] = None) -> int:
        if not _PURGE_LOCK.acquire(blocking=False):
            logger.info("Auto-purge job skipped: another instance is currently running.")
            return 0

        try:
            now_iso = self._now_utc(custom_now).isoformat()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id FROM contenidos 
                WHERE (purge_at <= ? OR purge_failed = 1) AND deleted_at IS NOT NULL 
                LIMIT ?
            """, (now_iso, batch_size))
            rows = cursor.fetchall()
            conn.close()

            purged_count = 0
            for r in rows:
                if self.delete_permanently(r["user_id"], r["id"], is_auto_purge=True, custom_now=custom_now):
                    purged_count += 1

            logger.info(f"Auto-purge completed: {purged_count} items purged.")
            return purged_count
        finally:
            _PURGE_LOCK.release()
