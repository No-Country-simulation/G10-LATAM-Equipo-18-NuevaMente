"""
embedding_service.py

Purpose:
    Generates vector embeddings for text using a multi-provider pipeline with
    automated token estimation, rate-limit management, batching, and cascade
    fallback across providers (Google Gemini -> Jina AI -> local sentence-transformers).
    Enforces identical output dimensions across all providers to maintain vector space
    compatibility within indexed documents.

Input:
    - text (str) or list of texts (List[str]) to embed.
    - is_query (bool): whether the embedding is for retrieval query or passage indexing.
    - model_name (Optional[str]): target model identifier to route query embeddings
      to the specific provider used during document indexing.

Output:
    - Single embedding: List[float]
    - Batch embeddings: List[List[float]]
    - model_name (str): tag identifying provider + model + dimension.
"""

import logging
import time
from typing import List, Optional

import numpy as np

from app.core.config import settings
from app.infrastructure.jina_client import JinaClient, TASK_PASSAGE, TASK_QUERY

logger = logging.getLogger(__name__)

# Task type used for Gemini embedding calls.
_GEMINI_TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
_GEMINI_TASK_QUERY = "RETRIEVAL_QUERY"

# Retry defaults for transient API failures.
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0


def estimate_tokens(texts: List[str]) -> int:
    """Estimates total tokens across texts using a 4-characters-per-token heuristic."""
    return sum(max(1, len(text) // 4) for text in texts)


class EmbeddingService:
    """
    Unified embedding interface supporting proactive routing, rate-limit aware
    batching, and atomic fallback across Gemini, Jina, and local models.
    """

    def __init__(
        self,
        method: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.method = method or settings.EMBEDDING_METHOD
        self.provider = provider or settings.EMBEDDING_API_PROVIDER
        self.dimensions = settings.EMBEDDING_DIMENSIONS

        self.model_id = self._resolve_model_id(self.provider if self.method != "local" else "local")
        self.model_name = f"{self.model_id}@{self.dimensions}"

        self._gemini_client = None
        self._jina_client = JinaClient(api_key=settings.JINA_API_KEY)
        self._model = None

        if self.method == "local":
            self._model = self._load_local_model()

        logger.info(
            "EmbeddingService initialized | method=%s provider=%s model=%s dimensions=%d",
            self.method,
            self.provider,
            self.model_name,
            self.dimensions,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def embed_text(
        self,
        text: str,
        is_query: bool = False,
        model_name: Optional[str] = None,
    ) -> List[float]:
        """
        Embeds a single text string. Routes to a specific provider if model_name is provided.
        """
        if model_name:
            provider = self._provider_from_model_name(model_name)
            try:
                vectors = self._embed_with_provider(provider, [text], is_query=is_query)
                self._validate_dimensions(vectors)
                return self._normalize(vectors)[0]
            except Exception as exc:
                logger.warning(
                    "Targeted embedding with model '%s' failed: %s. Using default pipeline.",
                    model_name,
                    exc,
                )

        return self.embed_batch([text], is_query=is_query)[0]

    def embed_batch(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        Embeds a list of texts using batching and provider cascade fallback.
        Ensures atomic provider usage across all texts in the batch.
        """
        if not texts:
            return []

        chain = self._resolve_execution_chain(texts)

        last_error: Optional[Exception] = None
        for candidate in chain:
            try:
                vectors = self._embed_with_provider(candidate, texts, is_query=is_query)
                self._validate_dimensions(vectors)
                normalized_vectors = self._normalize(vectors)

                self._apply_active_provider(candidate)
                return normalized_vectors
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Provider '%s' failed during embedding batch of %d items: %s. Proceeding to fallback.",
                    candidate,
                    len(texts),
                    exc,
                )

        raise RuntimeError(
            f"All embedding providers in fallback chain failed. Last error: {last_error}"
        ) from last_error

    # ── Routing and Fallback Chain ─────────────────────────────────────────────

    def _resolve_execution_chain(self, texts: List[str]) -> List[str]:
        """
        Determines the ordered list of providers based on token load and configured fallback.
        """
        if self.method == "local":
            return ["local"]

        estimated_tokens = estimate_tokens(texts)
        total_chunks = len(texts)

        # Proactive routing based on token volume against provider ceilings
        if self.provider == "gemini":
            if estimated_tokens > settings.GEMINI_SAFE_TPM:
                logger.info(
                    "Estimated tokens (%d in %d chunks) exceed Gemini safe threshold (%d TPM). Routing to Jina.",
                    estimated_tokens,
                    total_chunks,
                    settings.GEMINI_SAFE_TPM,
                )
                if estimated_tokens > settings.JINA_SAFE_TPM:
                    logger.info(
                        "Estimated tokens (%d) exceed Jina safe threshold (%d TPM). Routing to local model.",
                        estimated_tokens,
                        settings.JINA_SAFE_TPM,
                    )
                    return ["local"]
                return ["jina", "local"]
            return ["gemini", "jina", "local"]

        if self.provider == "jina":
            if estimated_tokens > settings.JINA_SAFE_TPM:
                logger.info(
                    "Estimated tokens (%d in %d chunks) exceed Jina safe threshold (%d TPM). Routing to local model.",
                    estimated_tokens,
                    total_chunks,
                    settings.JINA_SAFE_TPM,
                )
                return ["local"]
            return ["jina", "local"]

        return list(settings.EMBEDDING_FALLBACK_CHAIN)

    def _embed_with_provider(
        self,
        provider: str,
        texts: List[str],
        is_query: bool,
    ) -> List[List[float]]:
        """Dispatches embedding generation to the designated provider implementation."""
        if provider == "gemini":
            return self._embed_gemini_in_batches(texts, is_query=is_query)
        if provider == "jina":
            return self._embed_jina_in_batches(texts, is_query=is_query)
        if provider == "local":
            return self._embed_local(texts)
        raise ValueError(f"Unknown embedding provider: {provider}")

    def _apply_active_provider(self, provider: str) -> None:
        """Updates internal provider and model identification to match the successful provider."""
        self.provider = provider
        self.method = "local" if provider == "local" else "api"
        self.model_id = self._resolve_model_id(provider)
        self.model_name = f"{self.model_id}@{self.dimensions}"

    def _resolve_model_id(self, provider: str) -> str:
        """Maps a provider identifier to its configured model ID."""
        if provider == "local":
            return settings.LOCAL_EMBEDDING_MODEL
        return settings.EMBEDDING_API_MODELS.get(provider, settings.DEFAULT_EMBEDDING_MODEL)

    def _provider_from_model_name(self, model_name: str) -> str:
        """Extracts the provider key from a composite model_name string."""
        lower_name = model_name.lower()
        if "gemini" in lower_name:
            return "gemini"
        if "jina" in lower_name:
            return "jina"
        return "local"

    # ── Private: Gemini ────────────────────────────────────────────────────────

    def _get_gemini_client(self):
        """Initializes and caches the Google GenAI SDK client."""
        if self._gemini_client is None:
            from google import genai  # noqa: PLC0415
            self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._gemini_client

    def _embed_gemini_in_batches(self, texts: List[str], is_query: bool) -> List[List[float]]:
        """Processes texts in batches complying with Gemini request and token limits."""
        batch_size = settings.GEMINI_BATCH_SIZE
        results: List[List[float]] = []

        for start in range(0, len(texts), batch_size):
            chunk = texts[start:start + batch_size]
            results.extend(self._embed_gemini_chunk_with_retry(chunk, is_query=is_query))

        return results

    def _embed_gemini_chunk_with_retry(self, texts: List[str], is_query: bool) -> List[List[float]]:
        """Executes Gemini embedding for a batch with exponential backoff on retryable failures."""
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self._embed_gemini_direct(texts, is_query=is_query)
            except Exception as exc:
                last_error = exc
                # If a multi-text batch failed, attempt recursive split down to single text
                if len(texts) > 1 and attempt == 0:
                    logger.warning(
                        "Gemini batch of %d items failed: %s. Splitting batch in half.",
                        len(texts),
                        exc,
                    )
                    mid = len(texts) // 2
                    return (
                        self._embed_gemini_chunk_with_retry(texts[:mid], is_query=is_query)
                        + self._embed_gemini_chunk_with_retry(texts[mid:], is_query=is_query)
                    )

                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(
                        "Gemini request failed (attempt %d/%d): %s. Retrying in %.1fs.",
                        attempt + 1,
                        _MAX_RETRIES + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        raise RuntimeError(f"Gemini embedding failed after retries: {last_error}") from last_error

    def _embed_gemini_direct(self, texts: List[str], is_query: bool) -> List[List[float]]:
        """Sends batch payload directly to Google GenAI embedding endpoint."""
        from google.genai import types  # noqa: PLC0415

        client = self._get_gemini_client()
        task_type = _GEMINI_TASK_QUERY if is_query else _GEMINI_TASK_DOCUMENT
        model_id = self._resolve_model_id("gemini")

        # The SDK accepts a single string or a list of contents
        payload = texts if len(texts) > 1 else texts[0]

        result = client.models.embed_content(
            model=model_id,
            contents=payload,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimensions,
            ),
        )

        return [emb.values for emb in result.embeddings]

    # ── Private: Jina ──────────────────────────────────────────────────────────

    def _embed_jina_in_batches(self, texts: List[str], is_query: bool) -> List[List[float]]:
        """Processes texts in batches via Jina API client."""
        task = TASK_QUERY if is_query else TASK_PASSAGE
        batch_size = settings.JINA_BATCH_SIZE
        model_id = self._resolve_model_id("jina")

        return self._embed_jina_chunk(texts, model_id, task, batch_size)

    def _embed_jina_chunk(
        self,
        texts: List[str],
        model_id: str,
        task: str,
        batch_size: int,
    ) -> List[List[float]]:
        """Sends chunked requests to Jina with recursive batch reduction on failure."""
        if not texts:
            return []

        results: List[List[float]] = []
        for start in range(0, len(texts), batch_size):
            piece = texts[start:start + batch_size]
            try:
                results.extend(
                    self._jina_client.embed_batch(
                        piece,
                        model_name=model_id,
                        dimensions=self.dimensions,
                        task=task,
                    )
                )
            except Exception as exc:
                if batch_size == 1:
                    raise RuntimeError(f"Jina embedding failed for single text: {exc}") from exc
                logger.warning(
                    "Jina batch of %d items failed (%s). Halving batch size and retrying.",
                    len(piece),
                    exc,
                )
                results.extend(
                    self._embed_jina_chunk(piece, model_id, task, max(1, batch_size // 2))
                )

        return results

    # ── Private: Local ─────────────────────────────────────────────────────────

    def _load_local_model(self):
        """Loads SentenceTransformer model instance on demand."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            model_id = self._resolve_model_id("local")
            logger.info("Loading local embedding model: %s", model_id)
            return SentenceTransformer(model_id)
        except ImportError:
            logger.error(
                "sentence-transformers not installed. Install with: uv add sentence-transformers"
            )
            return None

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Computes embeddings locally using SentenceTransformer on CPU or GPU."""
        if self._model is None:
            self._model = self._load_local_model()

        if self._model is None:
            raise RuntimeError(
                "Local embedding model is unavailable. Install sentence-transformers or configure API keys."
            )

        embeddings = self._model.encode(
            texts,
            batch_size=settings.LOCAL_BATCH_SIZE,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    # ── Private: Validation & Normalization ────────────────────────────────────

    def _validate_dimensions(self, vectors: List[List[float]]) -> None:
        """Validates that all output vectors strictly match target dimensions."""
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise RuntimeError(
                    f"Embedding dimension mismatch: provider '{self.provider}' returned "
                    f"{len(vector)} dimensions, expected {self.dimensions}."
                )

    @staticmethod
    def _normalize(vectors: List[List[float]]) -> List[List[float]]:
        """Applies L2 normalization to vectors for exact cosine similarity calculation."""
        array = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(array, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return (array / norms).tolist()