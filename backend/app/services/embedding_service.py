"""
embedding_service.py

Purpose:
    Generates vector embeddings for text using a configurable provider.
    Supports Google Gemini API, Jina AI API, and a local sentence-transformers
    model as fallback. Tracks the active model name so the vector store can
    enforce that queries use the same model as the indexed documents.

Input:
    - text (str) or list of texts (List[str]) to embed.
    - Provider and model resolved from `settings` at instantiation time,
      overridable via constructor arguments.

Output:
    - Single embedding: List[float]
    - Batch embeddings: List[List[float]]
    - `model_name` (str): identifier of the model that produced the vectors,
      to be stored as collection metadata in the vector store.
"""

import logging
from typing import List, Optional

# google.generativeai and requests are imported lazily inside their methods
# to avoid ModuleNotFoundError when the package is not installed.

from app.core.config import settings

logger = logging.getLogger(__name__)

# Task type used for Gemini embedding calls — "RETRIEVAL_DOCUMENT" for indexing,
# "RETRIEVAL_QUERY" for query-time embedding.
_GEMINI_TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
_GEMINI_TASK_QUERY = "RETRIEVAL_QUERY"


class EmbeddingService:
    """
    Unified embedding interface. Resolves provider and model at init time
    and exposes a consistent `embed_text` / `embed_batch` API regardless
    of the underlying provider.
    """

    def __init__(
        self,
        method: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        # Resolve method and provider from settings if not explicitly overridden.
        self.method = method or settings.EMBEDDING_METHOD
        self.provider = provider or settings.EMBEDDING_API_PROVIDER

        # Resolve the concrete model name used — stored for collection tagging.
        if self.method == "local":
            self.model_name = settings.LOCAL_EMBEDDING_MODEL
            self._model = self._load_local_model()
        else:
            self.model_name = settings.EMBEDDING_API_MODELS.get(
                self.provider, settings.DEFAULT_EMBEDDING_MODEL
            )
            self._model = None  # API providers are stateless (HTTP calls)

        logger.info(
            "EmbeddingService initialized | method=%s provider=%s model=%s",
            self.method,
            self.provider,
            self.model_name,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        """
        Embeds a single text string.

        Args:
            text: The text to embed.
            is_query: True when embedding a search query (affects Gemini task type).

        Returns:
            Embedding vector as a list of floats.
        """
        if self.method == "local":
            return self._embed_local([text])[0]
        if self.provider == "gemini":
            return self._embed_gemini(text, is_query=is_query)
        if self.provider == "jina":
            return self._embed_jina_batch([text])[0]
        raise ValueError(f"Unknown embedding provider: {self.provider}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of texts in a single batched call where the provider
        supports it, falling back to sequential calls otherwise.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []
        if self.method == "local":
            return self._embed_local(texts)
        if self.provider == "gemini":
            # Gemini does not expose a public batch embed endpoint in the SDK;
            # sequential calls are used.
            return [self._embed_gemini(t, is_query=False) for t in texts]
        if self.provider == "jina":
            return self._embed_jina_batch(texts)
        raise ValueError(f"Unknown embedding provider: {self.provider}")

    # ── Private: Gemini ────────────────────────────────────────────────────────
    # Uses google-genai v2 SDK: Client(api_key=...) + client.models.embed_content(...)

    def _embed_gemini(self, text: str, is_query: bool = False) -> List[float]:
        try:
            try:
                from google import genai  # noqa: PLC0415
                from google.genai import types  # noqa: PLC0415

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                task_type = _GEMINI_TASK_QUERY if is_query else _GEMINI_TASK_DOCUMENT

                result = client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                return result.embeddings[0].values
            except Exception:
                import google.generativeai as ggenai  # noqa: PLC0415
                ggenai.configure(api_key=settings.GEMINI_API_KEY)
                task_type = "retrieval_query" if is_query else "retrieval_document"
                model_name = self.model_name if self.model_name.startswith("models/") else f"models/{self.model_name}"
                res = ggenai.embed_content(
                    model=model_name,
                    content=text,
                    task_type=task_type
                )
                return res["embedding"]
        except Exception as exc:
            logger.warning("Gemini embedding failed (%s). Falling back to cascade.", exc)
            return self._fallback_embed(text, failed_provider="gemini")

    # ── Private: Jina ──────────────────────────────────────────────────────────

    def _embed_jina_batch(self, texts: List[str]) -> List[List[float]]:
        from app.infrastructure.jina_client import JinaClient  # noqa: PLC0415
        
        try:
            client = JinaClient()
            return client.embed_batch(texts, self.model_name)
        except Exception as exc:
            logger.warning("Jina embedding failed (%s). Falling back to cascade.", exc)
            return [self._fallback_embed(t, failed_provider="jina") for t in texts]

    # ── Private: Local ─────────────────────────────────────────────────────────

    def _load_local_model(self):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("Loading local embedding model: %s", self.model_name)
            return SentenceTransformer(self.model_name)
        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Run: uv add sentence-transformers"
            )
            return None

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            self._model = self._load_local_model()
        if self._model is None:
            return [self._fallback_embed(t, failed_provider="local") for t in texts]
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    # ── Private: Fallback Cascade ──────────────────────────────────────────────

    def _fallback_embed(self, text: str, failed_provider: str) -> List[float]:
        """
        Cascada inteligente de fallbacks. 
        Si Gemini falla -> Jina (50% del texto) -> Local (25% del texto).
        """
        logger.warning(f"Activando fallback tras fallo de {failed_provider}")
        
        if failed_provider == "gemini":
            logger.info("Fallback a Jina AI (texto truncado al 50%)")
            try:
                # Truncamos texto a la mitad para Jina
                short_text = text[:max(1, len(text) // 2)]
                self.provider = "jina"
                self.model_name = settings.EMBEDDING_API_MODELS.get("jina", "jina-embeddings-v2-base-es")
                return self._embed_jina_batch([short_text])[0]
            except Exception as e:
                logger.error(f"Fallback Jina también falló: {e}")
                return self._fallback_embed(text, failed_provider="jina")
                
        elif failed_provider == "jina":
            logger.info("Fallback a Modelo Local (texto truncado al 25%)")
            try:
                # Truncamos texto a un cuarto para local
                short_text = text[:max(1, len(text) // 4)]
                self.method = "local"
                self.model_name = settings.LOCAL_EMBEDDING_MODEL
                if not self._model:
                    self._model = self._load_local_model()
                return self._embed_local([short_text])[0]
            except Exception as e:
                logger.error(f"Fallback Local también falló: {e}")
                return self._fallback_embed(text, failed_provider="local")
                
        # Deterministic emergency vector fallback (768-dim) when all API keys/local models are unconfigured
        import xxhash
        import numpy as np
        logger.warning("Generando embedding determinista de emergencia para texto (len=%d)", len(text))
        seed = int(xxhash.xxh64(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(768).astype(float)
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist() if norm > 0 else vec.tolist()
