"""
document_index_cache.py

Módulo de caché e indexación única por documento (hash_documento).
Evita re-extraer, re-segmentar y re-calcular embeddings para el mismo documento PDF.
Almacena fragmentos padre/hijo, embeddings y metadatos de ingesta en memoria/disco.
"""

import hashlib
import threading
import logging
from typing import Dict, Any, Optional

from app.services.text_cleaner import clean_text

logger = logging.getLogger("DocumentIndexCache")

class DocumentIndexCache:
    _instance: Optional["DocumentIndexCache"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._store: Dict[str, Dict[str, Any]] = {}
                cls._instance._indexing_locks: Dict[str, threading.Lock] = {}
            return cls._instance

    @staticmethod
    def compute_doc_hash(title: str, content: str) -> str:
        clean_t = (title or "").strip().lower()
        clean_c = clean_text(content or "")[:4000].strip()
        raw = f"{clean_t}:{clean_c}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_indexed_document(self, doc_hash: str) -> Optional[Dict[str, Any]]:
        return self._store.get(doc_hash)

    def set_indexed_document(self, doc_hash: str, index_data: Dict[str, Any]) -> None:
        self._store[doc_hash] = index_data
        logger.info(f"Documento indexado guardado en caché para hash: {doc_hash[:10]}")

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._indexing_locks.clear()
            logger.info("Caché de documentos limpiado por completo.")

    def get_doc_lock(self, doc_hash: str) -> threading.Lock:
        with self._lock:
            if doc_hash not in self._indexing_locks:
                self._indexing_locks[doc_hash] = threading.Lock()
            return self._indexing_locks[doc_hash]

