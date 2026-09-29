"""
reranker_service.py

Purpose:
    Reranks a small pool of candidate documents (parent chunks) against a
    query using a cross-encoder-style provider — Jina as primary, Cohere as
    fallback if Jina fails or is unavailable. Rerankers score (query, document)
    text pairs directly; they never touch embedding vectors, so they carry
    no dependency on EMBEDDING_DIMENSIONS.

Input:
    - query (str): the search query.
    - documents (List[str]): candidate document texts to score against the query.
    - top_n (int): how many top-scored documents to return.

Output:
    - List[Dict[str, Any]]: results sorted by relevance, each with
      {"index": <position in the input documents list>, "relevance_score": float}.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

_JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"
_JINA_RERANK_MODEL = "jina-reranker-v2-base-multilingual"
_COHERE_RERANK_MODEL = "rerank-multilingual-v3.0"

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2
_BASE_DELAY_SECONDS = 1.0


class BaseReranker(ABC):
    """Common interface so retrieval_service can try providers in order
    without knowing which one ultimately answered."""

    @abstractmethod
    def rerank(self, query: str, documents: List[str], top_n: int) -> List[Dict[str, Any]]:
        """Returns up to top_n results, sorted by relevance_score descending."""
        pass


class JinaReranker(BaseReranker):
    """Calls Jina AI's rerank endpoint. Retries transient (429/5xx) failures
    with exponential backoff before giving up."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.JINA_API_KEY

    def rerank(self, query: str, documents: List[str], top_n: int) -> List[Dict[str, Any]]:
        if not self.api_key or self.api_key == "your_jina_api_key_here":
            raise ValueError("JINA_API_KEY is missing or invalid.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _JINA_RERANK_MODEL,
            "query": query,
            "documents": documents,
            "top_n": top_n,
        }

        last_error: Exception = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = requests.post(_JINA_RERANK_URL, headers=headers, json=payload, timeout=30)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    raise requests.HTTPError(
                        f"Retryable status {response.status_code}: {response.text[:200]}"
                    )
                response.raise_for_status()
                data = response.json()
                return [
                    {"index": item["index"], "relevance_score": item["relevance_score"]}
                    for item in data["results"]
                ]
            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(
                        "Jina rerank failed (attempt %d/%d): %s. Retrying in %.1fs.",
                        attempt + 1, _MAX_RETRIES + 1, exc, delay,
                    )
                    time.sleep(delay)

        raise RuntimeError(f"Jina rerank failed after retries: {last_error}") from last_error


class CohereReranker(BaseReranker):
    """Wraps the existing CohereClient. Used only as a fallback when Jina
    fails, since Cohere's free trial tier has a low request-per-minute limit."""

    def __init__(self):
        from app.infrastructure.cohere_client import CohereClient  # noqa: PLC0415
        self._client_wrapper = CohereClient()

    def rerank(self, query: str, documents: List[str], top_n: int) -> List[Dict[str, Any]]:
        client = getattr(self._client_wrapper, "client", None)
        if client is None:
            raise RuntimeError("Cohere client is not configured (missing API key).")

        response = self._client_wrapper.rerank(
            model=_COHERE_RERANK_MODEL,
            query=query,
            documents=documents,
            top_n=top_n,
        )
        return [
            {"index": result.index, "relevance_score": float(result.relevance_score)}
            for result in response.results
        ]


def get_default_rerankers() -> List[BaseReranker]:
    """Returns the reranker chain in priority order: Jina first, Cohere as
    fallback. Construction is deferred to retrieval_service, which catches
    failures per-provider and tries the next one."""
    return [JinaReranker(), CohereReranker()]