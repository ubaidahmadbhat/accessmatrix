"""In-memory request rate limiting."""

import time
from collections import (
    defaultdict,
    deque,
)
from collections.abc import Callable
from math import ceil
from threading import Lock

Clock = Callable[[], float]


class RequestRateLimitError(RuntimeError):
    """Raised when a request exceeds its execution limit."""

    def __init__(
        self,
        retry_after_seconds: int,
    ) -> None:
        """Initialize a rate-limit error."""

        super().__init__("The request execution rate limit has been exceeded.")

        self.retry_after_seconds = retry_after_seconds


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window request limiter."""

    def __init__(
        self,
        *,
        limit: int = 30,
        window_seconds: float = 60.0,
        clock: Clock = time.monotonic,
    ) -> None:
        """Initialize the rate limiter."""

        if limit < 1:
            raise ValueError("The rate limit must be at least one.")

        if window_seconds <= 0:
            raise ValueError("The rate-limit window must be positive.")

        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock

        self._events: defaultdict[
            str,
            deque[float],
        ] = defaultdict(deque)

        self._lock = Lock()

    @property
    def limit(self) -> int:
        """Return the request limit."""

        return self._limit

    @property
    def window_seconds(self) -> float:
        """Return the window length."""

        return self._window_seconds

    def consume(
        self,
        key: str,
    ) -> int:
        """Consume one execution slot and return remaining slots."""

        now = self._clock()
        oldest_allowed = now - self._window_seconds

        with self._lock:
            events = self._events[key]

            while events and events[0] <= oldest_allowed:
                events.popleft()

            if len(events) >= self._limit:
                retry_after = max(
                    1,
                    ceil(self._window_seconds - (now - events[0])),
                )

                raise RequestRateLimitError(retry_after)

            events.append(now)

            return self._limit - len(events)
