"""
jina_client.py

Purpose:
    Thin HTTP client for the Jina AI embeddings endpoint. Isolated from
    EmbeddingService so the retry/backoff logic for transient network
    or rate-limit failures lives in a single place.

Input:
    - texts (List[str]): texts to embed in one HTTP call.
    - model_name (str): Jina model identifier (e.g. "jina-embeddings-v3").
    - dimensions (int): output vector size (Matryoshka truncation).
    - task (str): "retrieval.passage" for documents, "retrieval.query" for queries.

Output:
    - List[List[float]]: one embedding vector per input text, in the same order.
"""

import logging
import os
import time
from typing import List

import requests

logger = logging.getLogger("JinaClient")

# Jina task types used for asymmetric retrieval, matching the Gemini
# RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY distinction in embedding_service.py.
TASK_PASSAGE = "retrieval.passage"
TASK_QUERY = "retrieval.query"

# Transient HTTP statuses worth retrying: rate limit and server-side errors.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class JinaClient:
    """Native client for the Jina AI embeddings API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY", "")
        self.base_url = "https://api.jina.ai/v1/embeddings"

    def embed_batch(
        self,
        texts: List[str],
        model_name: str = "jina-embeddings-v3",
        dimensions: int = 768,
        task: str = TASK_PASSAGE,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
    ) -> List[List[float]]:
        """Embeds a batch of texts in a single request, retrying transient failures."""
        if not self.api_key or self.api_key == "your_jina_api_key_here":
            raise ValueError("JINA_API_KEY is missing or invalid.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "input": texts,
            "dimensions": dimensions,
            "task": task,
        }

        last_error: Exception = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    raise requests.HTTPError(
                        f"Retryable status {response.status_code}: {response.text[:200]}"
                    )
                response.raise_for_status()
                data = response.json()
                # Jina returns results sorted by index; re-sort defensively.
                return [
                    item["embedding"]
                    for item in sorted(data["data"], key=lambda x: x["index"])
                ]
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    delay = base_delay_seconds * (2 ** attempt)
                    logger.warning(
                        "Jina request failed (attempt %d/%d): %s. Retrying in %.1fs.",
                        attempt + 1, max_retries + 1, exc, delay,
                    )
                    time.sleep(delay)

        raise RuntimeError(f"Jina embedding request failed after retries: {last_error}") from last_error