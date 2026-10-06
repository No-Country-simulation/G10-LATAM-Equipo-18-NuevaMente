"""
embedding_rate_limiter.py

Purpose:
    Sliding-window rate limiter for embedding API providers. Tracks requests
    and tokens over the last 60 seconds and requests over the last 24 hours.
    Each text sent counts as one request, matching how Gemini bills embedding
    quota. State lives in process memory and is shared by every caller through
    the get_gemini_limiter() singleton, so several EmbeddingService instances
    (or a query during an indexing job) draw from the same budget.
    The daily window is a rolling 24h approximation of the provider's reset,
    and it starts empty whenever the process restarts.

Input:
    - Number of requests (texts) and estimated tokens about to be sent.
    - Limits from settings: GEMINI_SAFE_RPM, GEMINI_SAFE_TPM, GEMINI_SAFE_RPD.

Output:
    - reserve(): returns once the quota is reserved, or raises RateLimitExceeded.
    - estimate_wait(): total seconds a list of batches would have to wait,
      or None if they can never be sent (daily quota or batch too large).
    - daily_remaining(): requests left in the rolling 24h window.
"""

import threading
import time
from collections import deque
from typing import Callable, Deque, List, Optional, Sequence, Tuple

from app.core.config import settings

_WINDOW_SECONDS = 60.0
_DAY_SECONDS = 86400.0
_SAFETY_BUFFER_SECONDS = 0.25

# (timestamp, requests, tokens)
_Event = Tuple[float, int, int]


class RateLimitExceeded(Exception):
    """
    Raised when a reservation cannot be granted.
    kind: "per_minute" (only when non-blocking), "daily", or "batch_too_large".
    Waiting only helps for "per_minute".
    """

    def __init__(self, kind: str, wait_seconds: float = 0.0, message: str = ""):
        self.kind = kind
        self.wait_seconds = wait_seconds
        super().__init__(message or f"Rate limit exceeded ({kind}).")


def _seconds_until_fits(
    events: Sequence[_Event],
    now: float,
    requests: int,
    tokens: int,
    max_requests: int,
    max_tokens: int,
) -> float:
    """Seconds to wait until `requests`/`tokens` fit in the 60s window,
    releasing the oldest events one by one as they expire."""
    used_requests = sum(event[1] for event in events)
    used_tokens = sum(event[2] for event in events)

    if used_requests + requests <= max_requests and used_tokens + tokens <= max_tokens:
        return 0.0

    for timestamp, event_requests, event_tokens in events:
        used_requests -= event_requests
        used_tokens -= event_tokens
        if used_requests + requests <= max_requests and used_tokens + tokens <= max_tokens:
            return max(0.0, timestamp + _WINDOW_SECONDS - now) + _SAFETY_BUFFER_SECONDS

    # Unreachable when requests/tokens are within the limits (checked by callers).
    return _WINDOW_SECONDS


class SlidingWindowRateLimiter:
    """Thread-safe limiter with a 60s window (requests + tokens) and a 24h window (requests)."""

    def __init__(
        self,
        max_requests_per_minute: int,
        max_tokens_per_minute: int,
        max_requests_per_day: int,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self._max_rpm = max_requests_per_minute
        self._max_tpm = max_tokens_per_minute
        self._max_rpd = max_requests_per_day
        self._clock = clock
        self._sleeper = sleeper
        self._lock = threading.Lock()
        self._minute_events: Deque[_Event] = deque()
        self._day_events: Deque[Tuple[float, int]] = deque()

    # ── Public API ─────────────────────────────────────────────────────────────

    def reserve(
        self,
        requests: int,
        tokens: int,
        blocking: bool = True,
        on_wait: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Reserves quota for a batch about to be sent. Quota is recorded before
        the call because a failed call may still consume provider quota.
        When blocking, sleeps until the window has room (calling on_wait with
        the seconds first); when not blocking, raises RateLimitExceeded instead.
        """
        while True:
            with self._lock:
                now = self._clock()
                self._prune(now)
                self._check_reservable(requests, tokens)

                wait = _seconds_until_fits(
                    self._minute_events, now, requests, tokens, self._max_rpm, self._max_tpm
                )
                if wait == 0.0:
                    self._minute_events.append((now, requests, tokens))
                    self._day_events.append((now, requests))
                    return

            if not blocking:
                raise RateLimitExceeded("per_minute", wait, f"Per-minute quota full; retry in {wait:.1f}s.")

            if on_wait is not None:
                on_wait(wait)
            self._sleeper(wait)

    def estimate_wait(self, batches: List[Tuple[int, int]]) -> Optional[float]:
        """
        Simulates sending `batches` ((requests, tokens) each) back to back and
        returns the total seconds spent waiting. Returns None if the daily
        quota would be exceeded or a batch can never fit the per-minute limits.
        Does not reserve anything.
        """
        with self._lock:
            now = self._clock()
            self._prune(now)

            events: List[_Event] = list(self._minute_events)
            daily_used = self._daily_used()
            virtual_now = now
            total_wait = 0.0

            for requests, tokens in batches:
                if requests > self._max_rpm or tokens > self._max_tpm:
                    return None
                daily_used += requests
                if daily_used > self._max_rpd:
                    return None

                wait = _seconds_until_fits(
                    events, virtual_now, requests, tokens, self._max_rpm, self._max_tpm
                )
                virtual_now += wait
                total_wait += wait
                events = [event for event in events if event[0] + _WINDOW_SECONDS > virtual_now]
                events.append((virtual_now, requests, tokens))

            return total_wait

    def daily_remaining(self) -> int:
        """Requests still available in the rolling 24h window."""
        with self._lock:
            self._prune(self._clock())
            return max(0, self._max_rpd - self._daily_used())

    # ── Private ────────────────────────────────────────────────────────────────

    def _check_reservable(self, requests: int, tokens: int) -> None:
        """Raises for reservations that waiting can never satisfy."""
        if requests > self._max_rpm or tokens > self._max_tpm:
            raise RateLimitExceeded(
                "batch_too_large",
                message=(
                    f"Batch ({requests} requests, {tokens} tokens) exceeds per-minute limits "
                    f"({self._max_rpm} requests, {self._max_tpm} tokens)."
                ),
            )
        if self._daily_used() + requests > self._max_rpd:
            raise RateLimitExceeded(
                "daily",
                message=f"Daily quota exhausted ({self._max_rpd} requests per 24h).",
            )

    def _prune(self, now: float) -> None:
        """Drops events that fell outside their window."""
        while self._minute_events and self._minute_events[0][0] + _WINDOW_SECONDS <= now:
            self._minute_events.popleft()
        while self._day_events and self._day_events[0][0] + _DAY_SECONDS <= now:
            self._day_events.popleft()

    def _daily_used(self) -> int:
        return sum(event[1] for event in self._day_events)


# ---------------------------------------------------------------------------
# Shared Gemini limiter (one per process)
# ---------------------------------------------------------------------------

_gemini_limiter: Optional[SlidingWindowRateLimiter] = None
_gemini_limiter_lock = threading.Lock()


def get_gemini_limiter() -> SlidingWindowRateLimiter:
    """Returns the process-wide limiter for Gemini embeddings, creating it on first use."""
    global _gemini_limiter
    with _gemini_limiter_lock:
        if _gemini_limiter is None:
            _gemini_limiter = SlidingWindowRateLimiter(
                max_requests_per_minute=settings.GEMINI_SAFE_RPM,
                max_tokens_per_minute=settings.GEMINI_SAFE_TPM,
                max_requests_per_day=settings.GEMINI_SAFE_RPD,
            )
        return _gemini_limiter


def reset_gemini_limiter() -> None:
    """Discards the shared limiter so the next get_gemini_limiter() starts empty (used by tests)."""
    global _gemini_limiter
    with _gemini_limiter_lock:
        _gemini_limiter = None