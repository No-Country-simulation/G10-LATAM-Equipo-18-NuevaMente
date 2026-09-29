"""
embedding_service.py

Purpose:
    Generates vector embeddings for text using a multi-provider pipeline with
    token estimation, a shared rate limiter for Gemini, batching, progress
    reporting, and provider fallback (Google Gemini -> Jina AI -> local
    sentence-transformers). Enforces identical output dimensions across all
    providers so vectors stay compatible within one indexed document.

    Provider rules when embedding a list of texts:
    - Before sending anything, Gemini is checked against the shared limiter
      (daily quota, per-minute quota, estimated total wait). If it cannot
      serve the request, the next provider is used without spending quota.
    - Within one provider, texts are sent in batches. A failure before any
      vector was produced switches provider immediately. A failure after some
      batches succeeded waits and retries the failed batch on the same
      provider; when those retries run out, the partial vectors are discarded
      and the next provider re-embeds every text (vectors from different
      models are never mixed).
    - If every provider fails, the whole chain is retried after a pause, up to
      EMBEDDING_CHAIN_ROUNDS times.
    - Queries without a target model never wait for quota; they move to the
      next provider. Queries with a target model wait, because their vector
      must come from the same model as the index.

Input:
    - text (str) or list of texts (List[str]) to embed.
    - is_query (bool): whether the embedding is for a retrieval query or a passage.
    - model_name (Optional[str]): model identifier used to route a query to the
      provider that built the index.
    - on_progress (Optional[Callable[[dict], None]]): receives events with keys
      "stage", "message" (Spanish, ready to display) and optionally "current",
      "total", "wait_seconds", "provider". Stages: embedding, waiting,
      retrying, switching_provider.

    - check_local_available(): no input; reports whether the local model can be used.

Output:
    - Single embedding: List[float]
    - Batch embeddings: List[List[float]]
    - model_name (str): tag identifying provider + model + dimension.
    - check_local_available(): (available: bool, message: str), never raises.
"""

import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.infrastructure.jina_client import JinaClient, TASK_PASSAGE, TASK_QUERY
from app.services.embedding_rate_limiter import RateLimitExceeded, get_gemini_limiter

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[Dict[str, Any]], None]

# Task type used for Gemini embedding calls.
_GEMINI_TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
_GEMINI_TASK_QUERY = "RETRIEVAL_QUERY"

# Wait (seconds) before retrying a non rate-limit failure such as a transient 5xx.
_TRANSIENT_RETRY_WAIT_SECONDS = 5.0
# Bounds (seconds) applied to a retry delay suggested by the provider.
_MIN_RETRY_WAIT_SECONDS = 5.0
_MAX_RETRY_WAIT_SECONDS = 90.0

_PROVIDER_LABELS = {"gemini": "Gemini", "jina": "Jina", "local": "el modelo local"}

# Position limit of the local model's architecture; LOCAL_MAX_SEQ_LENGTH is capped to it.
_LOCAL_MODEL_MAX_POSITIONS = 512

# Local model shared by every EmbeddingService instance in the process, so it
# loads once. A failed load is remembered so later calls fail fast with the
# original reason instead of re-importing the libraries each time.
_local_model = None
_local_load_error: Optional[str] = None
_local_load_lock = threading.Lock()


def estimate_tokens(texts: List[str]) -> int:
    """Estimates total tokens across texts.

    Uses 3.5 characters per token — a conservative average that accounts for
    Spanish (shorter avg word length) and multilingual content common in
    NuevaMente. The value is intentionally slightly pessimistic so the
    proactive routing triggers before, not after, the real quota is hit.
    Avoids any API call so it never consumes RPM or RPD budget.
    """
    return sum(max(1, round(len(text) / 3.5)) for text in texts)


def _split_in_batches(texts: List[str], batch_size: int) -> List[List[str]]:
    """Splits texts into consecutive batches of at most batch_size items."""
    return [texts[start:start + batch_size] for start in range(0, len(texts), batch_size)]


class EmbeddingService:
    """
    Unified embedding interface supporting proactive routing, quota-aware
    batching, and provider fallback across Gemini, Jina, and local models.
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
        if self.method == "local":
            self.check_local_available()

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
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[float]:
        """
        Embeds a single text string. If model_name is provided, the text is
        embedded with that model's provider and waits for quota when needed,
        since the vector must match the index it will be compared against.
        """
        if model_name:
            provider = self._provider_from_model_name(model_name)
            try:
                vectors = self._run_provider(
                    provider, [text], is_query, on_progress, blocking=True
                )
                return self._finalize(vectors)[0]
            except Exception as exc:
                logger.warning(
                    "Targeted embedding with model '%s' failed: %s. Using default pipeline.",
                    model_name,
                    exc,
                )

        return self.embed_batch([text], is_query=is_query, on_progress=on_progress)[0]

    def embed_batch(
        self,
        texts: List[str],
        is_query: bool = False,
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[List[float]]:
        """
        Embeds a list of texts with one provider for the whole list, following
        the provider rules described in the module docstring.
        """
        if not texts:
            return []

        max_rounds = 1 if is_query else max(1, settings.EMBEDDING_CHAIN_ROUNDS)
        last_error: Optional[Exception] = None

        for round_number in range(1, max_rounds + 1):
            chain = self._resolve_execution_chain(texts, is_query)

            for position, candidate in enumerate(chain):
                try:
                    vectors = self._run_provider(
                        candidate, texts, is_query, on_progress, blocking=not is_query
                    )
                    finalized = self._finalize(vectors)
                    self._apply_active_provider(candidate)
                    return finalized
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Provider '%s' failed for %d texts: %s.", candidate, len(texts), exc
                    )
                    if position + 1 < len(chain):
                        self._emit(
                            on_progress,
                            "switching_provider",
                            f"{_PROVIDER_LABELS[candidate].capitalize()} no pudo completar; "
                            f"cambiando a {_PROVIDER_LABELS[chain[position + 1]]}…",
                            provider=chain[position + 1],
                        )

            if round_number < max_rounds:
                wait = float(settings.EMBEDDING_RETRY_WAIT_SECONDS)
                logger.warning(
                    "All providers failed (round %d/%d). Waiting %.0fs before retrying the chain.",
                    round_number, max_rounds, wait,
                )
                self._emit(
                    on_progress,
                    "waiting",
                    f"Todos los proveedores fallaron. Reintentando en {wait:.0f}s "
                    f"(ronda {round_number + 1}/{max_rounds})…",
                    wait_seconds=wait,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"All embedding providers in fallback chain failed. Last error: {last_error}"
        ) from last_error

    # ── Routing ────────────────────────────────────────────────────────────────

    def _resolve_execution_chain(self, texts: List[str], is_query: bool) -> List[str]:
        """
        Returns the ordered providers to try, dropping the ones that a
        pre-check shows cannot serve this request.
        """
        if self.method == "local":
            return ["local"]

        if self.provider == "gemini":
            base_chain = ["gemini", "jina", "local"]
        elif self.provider == "jina":
            base_chain = ["jina", "local"]
        else:
            base_chain = list(settings.EMBEDDING_FALLBACK_CHAIN)

        return [p for p in base_chain if self._provider_can_serve(p, texts, is_query)]

    def _provider_can_serve(self, provider: str, texts: List[str], is_query: bool) -> bool:
        """Pre-check that decides, without sending anything, whether a provider is worth trying."""
        if provider == "gemini":
            return self._gemini_can_serve(texts, is_query)

        if provider == "jina":
            estimated_tokens = estimate_tokens(texts)
            if estimated_tokens > settings.JINA_SAFE_TPM:
                logger.info(
                    "Estimated tokens (%d in %d chunks) exceed Jina safe threshold (%d TPM). Skipping Jina.",
                    estimated_tokens, len(texts), settings.JINA_SAFE_TPM,
                )
                return False

        return True

    def _gemini_can_serve(self, texts: List[str], is_query: bool) -> bool:
        """
        Uses the shared limiter to simulate sending every batch. Gemini is
        skipped if the daily quota cannot cover it, or if the total wait would
        exceed GEMINI_MAX_WAIT_SECONDS (or any wait at all for untargeted queries).
        """
        batch_size = self._batch_size_for("gemini", len(texts))
        batches = [
            (len(chunk), estimate_tokens(chunk))
            for chunk in _split_in_batches(texts, batch_size)
        ]

        total_wait = get_gemini_limiter().estimate_wait(batches)
        if total_wait is None:
            logger.info(
                "Gemini cannot serve %d texts (daily quota or per-minute limits). Skipping Gemini.",
                len(texts),
            )
            return False

        max_wait = 0.0 if is_query else float(settings.GEMINI_MAX_WAIT_SECONDS)
        if total_wait > max_wait:
            logger.info(
                "Gemini would need %.0fs of waiting for %d texts (max %.0fs). Skipping Gemini.",
                total_wait, len(texts), max_wait,
            )
            return False

        return True

    # ── Per-provider execution ─────────────────────────────────────────────────

    def _run_provider(
        self,
        provider: str,
        texts: List[str],
        is_query: bool,
        on_progress: Optional[ProgressCallback],
        blocking: bool,
    ) -> List[List[float]]:
        """
        Embeds every text with one provider, batch by batch.
        - Failure before any vector exists: raised right away so the caller switches provider.
        - Failure after some batches succeeded: waits and retries the same batch,
          up to EMBEDDING_PARTIAL_RETRIES times, then raises (partial vectors are dropped).
        """
        label = _PROVIDER_LABELS[provider]
        batch_size = self._batch_size_for(provider, len(texts))
        vectors: List[List[float]] = []
        retries_used = 0
        start = 0

        while start < len(texts):
            batch = texts[start:start + batch_size]
            try:
                vectors.extend(
                    self._embed_batch_with_split(provider, batch, is_query, on_progress, blocking)
                )
            except Exception as exc:
                if not vectors:
                    raise
                if isinstance(exc, RateLimitExceeded) and exc.kind != "per_minute":
                    raise  # daily quota or oversized batch: waiting cannot help
                if retries_used >= settings.EMBEDDING_PARTIAL_RETRIES:
                    raise RuntimeError(
                        f"{provider} failed after {retries_used} retries with "
                        f"{len(vectors)}/{len(texts)} texts done; partial results discarded: {exc}"
                    ) from exc

                retries_used += 1
                wait = self._wait_seconds_for_error(exc)
                logger.warning(
                    "%s failed at %d/%d texts: %s. Waiting %.0fs (retry %d/%d).",
                    provider, len(vectors), len(texts), exc, wait,
                    retries_used, settings.EMBEDDING_PARTIAL_RETRIES,
                )
                self._emit(
                    on_progress,
                    "retrying",
                    f"Reintentando con {label} en {wait:.0f}s "
                    f"({retries_used}/{settings.EMBEDDING_PARTIAL_RETRIES})…",
                    current=len(vectors), total=len(texts), wait_seconds=wait, provider=provider,
                )
                time.sleep(wait)
                continue

            start += len(batch)
            self._emit(
                on_progress,
                "embedding",
                f"Generando embeddings con {label}: {start}/{len(texts)}",
                current=start, total=len(texts), provider=provider,
            )

        return vectors

    def _embed_batch_with_split(
        self,
        provider: str,
        batch: List[str],
        is_query: bool,
        on_progress: Optional[ProgressCallback],
        blocking: bool,
    ) -> List[List[float]]:
        """Sends one batch; if the provider rejects its size or payload, splits it in half and retries each half."""
        try:
            return self._call_provider(provider, batch, is_query, on_progress, blocking)
        except Exception as exc:
            if len(batch) > 1 and self._is_splittable_error(provider, exc):
                logger.warning(
                    "%s rejected a batch of %d texts: %s. Splitting in half.", provider, len(batch), exc
                )
                middle = len(batch) // 2
                return (
                    self._embed_batch_with_split(provider, batch[:middle], is_query, on_progress, blocking)
                    + self._embed_batch_with_split(provider, batch[middle:], is_query, on_progress, blocking)
                )
            raise

    def _call_provider(
        self,
        provider: str,
        batch: List[str],
        is_query: bool,
        on_progress: Optional[ProgressCallback],
        blocking: bool,
    ) -> List[List[float]]:
        """Performs one provider call. Gemini calls first reserve quota in the shared limiter."""
        if provider == "gemini":
            def announce_wait(seconds: float) -> None:
                self._emit(
                    on_progress,
                    "waiting",
                    f"Esperando {seconds:.0f}s para no saturar Gemini…",
                    wait_seconds=seconds, provider="gemini",
                )

            get_gemini_limiter().reserve(
                requests=len(batch),
                tokens=estimate_tokens(batch),
                blocking=blocking,
                on_wait=announce_wait,
            )
            return self._embed_gemini_direct(batch, is_query=is_query)

        if provider == "jina":
            return self._embed_jina_batch(batch, is_query=is_query)

        if provider == "local":
            return self._embed_local(batch)

        raise ValueError(f"Unknown embedding provider: {provider}")

    @staticmethod
    def _batch_size_for(provider: str, total_texts: int) -> int:
        """Batch size per provider. Gemini is also capped by the safe RPM, since each text counts as a request."""
        if provider == "gemini":
            return max(1, min(settings.GEMINI_BATCH_SIZE, settings.GEMINI_SAFE_RPM))
        if provider == "jina":
            return max(1, settings.JINA_BATCH_SIZE)
        return max(1, total_texts)

    # ── Error classification ───────────────────────────────────────────────────

    @staticmethod
    def _error_code(exc: Exception) -> Optional[int]:
        """Extracts an HTTP-like status code from an SDK exception, if present."""
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        return code if isinstance(code, int) else None

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        """True for provider 429 / quota errors."""
        if self._error_code(exc) == 429:
            return True
        text = str(exc)
        return "RESOURCE_EXHAUSTED" in text or re.search(r"\b429\b", text) is not None

    def _is_splittable_error(self, provider: str, exc: Exception) -> bool:
        """True when splitting the batch can fix the failure (payload/size errors, never quota errors)."""
        if isinstance(exc, RateLimitExceeded) or self._is_rate_limit_error(exc):
            return False
        if provider == "gemini":
            return self._error_code(exc) == 400 or "INVALID_ARGUMENT" in str(exc)
        return provider == "jina"

    def _wait_seconds_for_error(self, exc: Exception) -> float:
        """Seconds to wait before retrying: the provider's suggested delay for rate limits, else a short default."""
        if isinstance(exc, RateLimitExceeded) and exc.wait_seconds > 0:
            return exc.wait_seconds

        if self._is_rate_limit_error(exc):
            match = re.search(r"retry(?:Delay|\s+in)\D{0,5}(\d+(?:\.\d+)?)\s*s", str(exc), re.IGNORECASE)
            if match:
                suggested = float(match.group(1)) + 1.0
                return min(max(suggested, _MIN_RETRY_WAIT_SECONDS), _MAX_RETRY_WAIT_SECONDS)
            return float(settings.EMBEDDING_RETRY_WAIT_SECONDS)

        return _TRANSIENT_RETRY_WAIT_SECONDS

    # ── Progress reporting ─────────────────────────────────────────────────────

    @staticmethod
    def _emit(on_progress: Optional[ProgressCallback], stage: str, message: str, **extra: Any) -> None:
        """Sends a progress event to the callback; a failing callback never breaks embedding."""
        if on_progress is None:
            return
        try:
            on_progress({"stage": stage, "message": message, **extra})
        except Exception as exc:
            logger.warning("Progress callback raised an error and was ignored: %s", exc)

    # ── Provider identity ──────────────────────────────────────────────────────

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

    def _embed_jina_batch(self, texts: List[str], is_query: bool) -> List[List[float]]:
        """Sends one batch to the Jina API client."""
        return self._jina_client.embed_batch(
            texts,
            model_name=self._resolve_model_id("jina"),
            dimensions=self.dimensions,
            task=TASK_QUERY if is_query else TASK_PASSAGE,
        )

    # ── Private: Local ─────────────────────────────────────────────────────────

    def check_local_available(self) -> Tuple[bool, str]:
        """
        Loads the local model if needed and reports whether it can be used,
        without raising. Meant to run at application startup so a missing
        dependency shows up early instead of in the middle of a fallback.
        """
        model = self._load_local_model()
        if model is None:
            return False, _local_load_error or "Local embedding model is unavailable."

        model_dimension = model.get_sentence_embedding_dimension()
        if model_dimension != self.dimensions:
            message = (
                f"Local model produces {model_dimension} dimensions but EMBEDDING_DIMENSIONS "
                f"is {self.dimensions}; its vectors would be rejected."
            )
            logger.error(message)
            return False, message

        message = f"Local model ready ({self._resolve_model_id('local')}, {model_dimension} dimensions)."
        logger.info(message)
        return True, message

    def _load_local_model(self):
        """
        Returns the shared SentenceTransformer instance, loading it on first use.
        Returns None and remembers the reason if loading fails; the full
        traceback is logged once, at the moment of the failure.
        """
        global _local_model, _local_load_error

        with _local_load_lock:
            if _local_model is not None:
                return _local_model
            if _local_load_error is not None:
                return None

            model_id = self._resolve_model_id("local")
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                logger.info("Loading local embedding model: %s", model_id)
                model = SentenceTransformer(model_id)
                model.max_seq_length = min(settings.LOCAL_MAX_SEQ_LENGTH, _LOCAL_MODEL_MAX_POSITIONS)
                _local_model = model
                return model
            except Exception as exc:
                # ModuleNotFoundError carries the name of the missing module; a missing
                # dependency of sentence-transformers is reported differently from the
                # package itself being absent.
                if isinstance(exc, ModuleNotFoundError) and exc.name == "sentence_transformers":
                    _local_load_error = (
                        "sentence-transformers is not installed. Install with: uv add sentence-transformers"
                    )
                elif isinstance(exc, ModuleNotFoundError):
                    _local_load_error = (
                        f"Missing dependency '{exc.name}' required by sentence-transformers/transformers: {exc}"
                    )
                else:
                    _local_load_error = (
                        f"Local model '{model_id}' failed to load: {type(exc).__name__}: {exc}"
                    )
                logger.error(_local_load_error, exc_info=True)
                return None

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Computes embeddings locally using SentenceTransformer on CPU or GPU."""
        model = self._load_local_model()
        if model is None:
            raise RuntimeError(f"Local embedding model is unavailable: {_local_load_error}")

        self._warn_if_truncated(model, texts)

        embeddings = model.encode(
            texts,
            batch_size=settings.LOCAL_BATCH_SIZE,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    @staticmethod
    def _warn_if_truncated(model, texts: List[str]) -> None:
        """Logs how many texts exceed the model's max sequence length (the library truncates them silently)."""
        try:
            token_ids = model.tokenizer(texts, add_special_tokens=True)["input_ids"]
            too_long = sum(1 for ids in token_ids if len(ids) > model.max_seq_length)
        except Exception:
            return  # Diagnostic only: never block embedding because the check failed.

        if too_long:
            logger.warning(
                "%d of %d texts exceed the local model's max_seq_length (%d tokens) and will be truncated.",
                too_long, len(texts), model.max_seq_length,
            )

    # ── Private: Validation & Normalization ────────────────────────────────────

    def _finalize(self, vectors: List[List[float]]) -> List[List[float]]:
        """Validates dimensions and L2-normalizes the vectors."""
        self._validate_dimensions(vectors)
        return self._normalize(vectors)

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