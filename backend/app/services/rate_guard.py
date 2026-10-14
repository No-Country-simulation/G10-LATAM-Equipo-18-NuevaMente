"""
rate_guard.py

Purpose:
    Process-wide pacing + circuit breaker for LLM API calls, mirroring the
    embedding limiter philosophy: a shared singleton so every AgentOrchestrator
    instance in the process draws from the same budget and failure memory.

Difference from the embedding limiter:
    - Paces calls per provider (RPM), but does not track separate token quota.
    - Adds a consecutive-failure cooldown: a model that fails N times in a row
      (503 high-demand, quota, 404) is skipped for COOLDOWN_SECONDS instead of
      being retried on every batch.
"""

import logging
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger("LlmRateGuard")

INTERVAL_SECONDS = 3.5      # Gemini flash tier allows ~15 req/min (4s gap); Groq is faster
COOLDOWN_SECONDS = 60.0     # skip an unhealthy model for 1 min
FAILURE_THRESHOLD = 2       # consecutive failures before cooling down


class LlmRateGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_call: Dict[str, float] = {}       # provider -> last call timestamp
        self._failures: Dict[str, int] = {}          # "provider:model" -> consecutive failures
        self._cooldown_until: Dict[str, float] = {}  # "provider:model" -> skip until
        self._in_cooldown: Dict[str, bool] = {}      # while True, skip attempts

    def should_attempt(self, provider: str, model: Optional[str]) -> bool:
        key = f"{provider}:{model}"
        with self._lock:
            if self._cooldown_until.get(key, 0.0) > time.monotonic():
                logger.info("Saltando %s en pausa (%.0fs restantes).", key, self._cooldown_until[key] - time.monotonic())
                return False
            if self._in_cooldown.get(key, False) and time.monotonic() >= self._cooldown_until[key]:
                self._in_cooldown[key] = False
            return True

    def wait_for_slot(self, provider: str, model: Optional[str]) -> None:
        """Blocks until at least INTERVAL_SECONDS passed since the last call to this provider."""
        while True:
            with self._lock:
                wait = self._last_call.get(provider, 0.0) + INTERVAL_SECONDS - time.monotonic()
                if wait <= 0:
                    self._last_call[provider] = time.monotonic()
                    return
            time.sleep(wait)

    def record_success(self, provider: str, model: Optional[str]) -> None:
        with self._lock:
            self._failures.pop(f"{provider}:{model}", None)

    def record_failure(self, provider: str, model: Optional[str]) -> None:
        key = f"{provider}:{model}"
        with self._lock:
            if self._in_cooldown.get(key, False):
                return
            self._failures[key] = self._failures.get(key, 0) + 1
            if self._failures[key] >= FAILURE_THRESHOLD:
                self._cooldown_until[key] = time.monotonic() + COOLDOWN_SECONDS
                self._in_cooldown[key] = True
                self._failures[key] = 0
                logger.warning("%s entró en pausa por %d fallos consecutivos (%ds).", key, FAILURE_THRESHOLD, COOLDOWN_SECONDS)


_guard: Optional[LlmRateGuard] = None
_guard_lock = threading.Lock()


def get_llm_guard() -> LlmRateGuard:
    """Returns the process-wide LLM guard, creating it on first use."""
    global _guard
    with _guard_lock:
        if _guard is None:
            _guard = LlmRateGuard()
        return _guard