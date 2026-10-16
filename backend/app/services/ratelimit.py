"""A small in-memory sliding-window rate limiter (per process: it resets when the server restarts)."""

import math
import threading
import time
from collections import deque
from collections.abc import Callable, Hashable


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._max = max_events
        self._window = window_seconds
        self._clock = clock  # injectable, so tests can control time
        self._events: dict[Hashable, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: Hashable) -> int:
        """Record one event for `key` and return 0, or return how many seconds to wait if the limit is reached."""
        with self._lock:
            now = self._clock()
            events = self._events.setdefault(key, deque())
            while events and events[0] <= now - self._window:
                events.popleft()
            if len(events) >= self._max:
                return max(1, math.ceil(events[0] + self._window - now))
            events.append(now)
            return 0