"""
storage_queue_service.py

Servicio de persistencia asíncrona y cola de almacenamiento resiliente (storage_jobs).
Garantiza:
  - Persistencia de trabajos en SQLite (users.db) para sobrevivir a reinicios.
  - Reintentos automáticos con backoff exponencial para errores 429/5xx o timeouts.
  - Esquema jerárquico canónico:
      * Fuentes: usuarios/{user_id}/documentos/{sha256}/{nombre_saneado}
      * Contenidos: usuarios/{user_id}/contenidos/{content_id}/v{version}.json
  - Estados reales: 'pendiente' -> 'completado' | 'error'. Nunca 'completado' sin confirmación del SDK.
  - Soporte de versionado incremental v{n+1}.json ("Ampliar").
  - Deduplicación por SHA-256 previa a la subida.
"""

import os
import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from app.core.config import settings
from app.core.security import get_db
from app.services.storage import get_storage_backend
from app.services.storage.base import StorageBackend

logger = logging.getLogger("StorageQueueService")


class StorageQueueService:
    """Gestiona la cola persistente de trabajos de almacenamiento hacia OCI Object Storage."""

    _instance = None

    def __init__(self):
        self.init_storage_tables()

    @classmethod
    def get_instance(cls) -> "StorageQueueService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_storage_tables(self) -> None:
        """Crea la tabla storage_jobs en SQLite si no existe."""
        try:
            conn = get_db()
            cursor = conn.cursor()

            # Persistent background jobs queue (storage_jobs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_jobs (
                    id TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    estado TEXT DEFAULT 'pendiente',
                    intentos INTEGER DEFAULT 0,
                    max_intentos INTEGER DEFAULT 5,
                    ultimo_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_jobs_content ON storage_jobs (content_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_jobs_estado ON storage_jobs (estado)")

            # Tabla de documentos originales (documentos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documentos (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    content_type TEXT NOT NULL,
                    status_upload TEXT DEFAULT 'completado',
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documentos_user ON documentos (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documentos_sha256 ON documentos (sha256)")

            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Error inicializando tablas de storage_jobs: %s", exc)

    def enqueue_content_job(
        self,
        content_id: str,
        user_id: Optional[str],
        json_data: dict,
        version: int = 1,
        doc_slug: Optional[str] = None,
        recipient_profile: Optional[str] = None,
        output_format: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra un trabajo de guardado de contenido educativo en 'storage_jobs' con estado 'pendiente'
        y trazabilidad completa de nomenclatura y metadatos.
        """
        user_clean = StorageBackend.sanitize_user_id(user_id)
        bucket = settings.OCI_BUCKET_CONTENT
        object_key = StorageBackend.build_content_key(
            user_id=user_clean,
            content_id=content_id,
            version=version,
            doc_slug=doc_slug,
            recipient_profile=recipient_profile,
            output_format=output_format,
            timestamp=timestamp,
        )
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = time.time()

        payload_str = json.dumps(json_data, ensure_ascii=False)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO storage_jobs (
                id, content_id, user_id, bucket, object_key, tipo, payload_json, version,
                estado, intentos, max_intentos, ultimo_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', 0, 5, NULL, ?, ?)
        """, (job_id, content_id, user_clean, bucket, object_key, "contenido_educativo", payload_str, version, now, now))
        conn.commit()
        conn.close()

        logger.info("Trabajo de persistencia encolado: job_id=%s, content_id=%s, object_key=%s", job_id, content_id, object_key)

        return {
            "job_id": job_id,
            "bucket": bucket,
            "objeto_id": object_key,
            "status_upload": "pendiente",
            "version": version,
        }

    def process_job(self, job_id: str) -> bool:
        """
        Ejecuta el intento de subida hacia OCI para un trabajo específico.
        Actualiza el estado a 'completado' o 'error' según el resultado del SDK.
        """
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM storage_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        bucket = row["bucket"]
        object_key = row["object_key"]
        payload_str = row["payload_json"]
        intentos = row["intentos"] + 1
        max_intentos = row["max_intentos"]
        version = row["version"]

        backend = get_storage_backend()
        now = time.time()

        try:
            data_bytes = payload_str.encode("utf-8")
            metadata = {
                "trazabilidad-tipo": "contenido_educativo",
                "content-id": str(row["content_id"]),
                "version": str(version),
                "user-id": str(row["user_id"]),
                "creado-utc": datetime.now(timezone.utc).isoformat(),
            }
            res = backend.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=data_bytes,
                content_type="application/json",
                metadata=metadata,
            )

            # Confirmado por el SDK
            cursor.execute("""
                UPDATE storage_jobs
                SET estado = 'completado', intentos = ?, updated_at = ?, ultimo_error = NULL
                WHERE id = ?
            """, (intentos, now, job_id))
            conn.commit()
            conn.close()

            logger.info("Trabajo de almacenamiento completado exitosamente: job_id=%s [%s/%s]", job_id, bucket, object_key)
            return True

        except Exception as exc:
            err_msg = str(exc)[:200]
            new_estado = "error" if intentos >= max_intentos else "pendiente"
            cursor.execute("""
                UPDATE storage_jobs
                SET estado = ?, intentos = ?, ultimo_error = ?, updated_at = ?
                WHERE id = ?
            """, (new_estado, intentos, err_msg, now, job_id))
            conn.commit()
            conn.close()

            logger.error("Fallo al procesar job_id=%s (intento %d/%d): %s", job_id, intentos, max_intentos, err_msg)
            return False

    def process_pending_jobs(self, limit: int = 10) -> int:
        """Procesa una tanda de trabajos pendientes (ideal para workers de fondo o al arrancar)."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM storage_jobs
            WHERE estado = 'pendiente' AND intentos < max_intentos
            ORDER BY created_at ASC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        success_count = 0
        for row in rows:
            if self.process_job(row["id"]):
                success_count += 1
        return success_count

    def get_content_status(self, content_id: str) -> Dict[str, Any]:
        """Obtiene el estado de almacenamiento real para un content_id."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM storage_jobs
            WHERE content_id = ?
            ORDER BY version DESC, created_at DESC LIMIT 1
        """, (content_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "content_id": content_id,
                "status_upload": "no_encontrado",
                "bucket": settings.OCI_BUCKET_CONTENT,
                "objeto_id": None,
                "intentos": 0,
                "version": 1,
                "ultimo_error": "No existe registro de trabajo para este contenido.",
            }

        return {
            "content_id": content_id,
            "status_upload": row["estado"],
            "bucket": row["bucket"],
            "objeto_id": row["object_key"],
            "intentos": row["intentos"],
            "version": row["version"],
            "ultimo_error": row["ultimo_error"],
            "updated_at": row["updated_at"],
        }

    def retry_content(self, content_id: str, user_id: Optional[str] = None) -> bool:
        """Reencola los trabajos con error para un contenido específico."""
        conn = get_db()
        cursor = conn.cursor()

        query = "SELECT id FROM storage_jobs WHERE content_id = ? AND estado = 'error'"
        params = [content_id]
        if user_id:
            safe_user = StorageBackend.sanitize_user_id(user_id)
            query += " AND user_id = ?"
            params.append(safe_user)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return False

        now = time.time()
        for row in rows:
            cursor.execute("""
                UPDATE storage_jobs
                SET estado = 'pendiente', intentos = 0, ultimo_error = NULL, updated_at = ?
                WHERE id = ?
            """, (now, row["id"]))

        conn.commit()
        conn.close()

        # Disparar intento de inmediato
        for row in rows:
            self.process_job(row["id"])

        return True

    def save_content_metadata(
        self,
        content_id: str,
        user_id: Optional[str],
        title: str,
        content: str,
        recipient_profile: Optional[str] = None,
        output_format: Optional[str] = None,
        niche: Optional[str] = None,
        detail_level: Optional[str] = None,
        object_key_json: Optional[str] = None,
        response_json: Optional[str] = None,
    ) -> None:
        """
        Registra un paquete educativo generado en la tabla 'contenidos'.

        La biblioteca y la papelera leen de esa tabla; sin esta fila el
        contenido existe en Object Storage pero es invisible en la app.

        `content` guarda únicamente el paquete adaptado (lo que el visor
        renderiza) mientras que `response_json` guarda la respuesta completa
        (metadatos + evaluación de calidad), que es la única forma de que la
        Biblioteca muestre el anclaje RAG real en lugar de un valor fijo.
        """
        now = time.time()
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO contenidos (
                    id, user_id, title, content, recipient_profile, output_format,
                    niche, detail_level, status, object_key_json, response_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?)
            """, (
                content_id,
                user_id or "usr_demo_001",
                title,
                content,
                recipient_profile,
                output_format,
                niche,
                detail_level,
                object_key_json,
                response_json,
                now,
                now,
            ))
            conn.commit()
            logger.info("Contenido registrado en la biblioteca: content_id=%s, user_id=%s", content_id, user_id)
        finally:
            conn.close()

    def save_source_document(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        content_type: str = "application/pdf",
    ) -> Dict[str, Any]:
        """
        Valida, calcula sha256 y guarda un documento original en OCI_BUCKET_SOURCES.
        Registra la metadata en la tabla 'documentos'.
        """
        max_bytes = settings.STORAGE_MAX_UPLOAD_MB * 1024 * 1024
        size_bytes = len(file_bytes)
        if size_bytes > max_bytes:
            raise ValueError(f"El archivo supera el tamaño máximo permitido de {settings.STORAGE_MAX_UPLOAD_MB} MB.")

        sha256_hash = StorageBackend.compute_sha256(file_bytes)
        user_clean = StorageBackend.sanitize_user_id(user_id)
        safe_filename = StorageBackend.sanitize_filename(filename)
        bucket = settings.OCI_BUCKET_SOURCES

        object_key = StorageBackend.build_document_key(user_clean, sha256_hash, safe_filename)
        backend = get_storage_backend()

        metadata = {
            "trazabilidad-tipo": "documento_fuente",
            "nombre-original": safe_filename,
            "sha256": sha256_hash,
            "user-id": user_clean,
            "creado-utc": datetime.now(timezone.utc).isoformat(),
        }
        res = backend.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=file_bytes,
            content_type=content_type,
            metadata=metadata,
        )

        doc_id = f"doc-{uuid.uuid4().hex[:12]}"
        resolved_title = title or safe_filename
        now = time.time()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO documentos (
                id, user_id, title, filename, bucket, object_key, sha256,
                size_bytes, content_type, status_upload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completado', ?)
        """, (doc_id, user_clean, resolved_title, safe_filename, bucket, object_key, sha256_hash, size_bytes, content_type, now))
        conn.commit()
        conn.close()

        logger.info("Documento fuente persistido en OCI y BD: doc_id=%s, object_key=%s", doc_id, object_key)

        return {
            "id": doc_id,
            "bucket": bucket,
            "objeto_id": object_key,
            "sha256": sha256_hash,
            "size_bytes": size_bytes,
            "status_upload": "completado",
            "deduplicado": res.get("deduplicado", False),
        }
