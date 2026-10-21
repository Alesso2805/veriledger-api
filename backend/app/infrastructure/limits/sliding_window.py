import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    """Counts events per key over a sliding window, in this process's memory (one API process, ADR-0005)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._events: dict[str, deque[float]] = {}

    def hit(self, key: str, limit: int, window_seconds: float) -> float | None:
        """Records an event and returns None; or, if the key already has `limit` events in the window,
        records nothing and returns the seconds until the oldest of them leaves it."""
        now = self._clock()
        events = self._events.setdefault(key, deque())
        while events and events[0] <= now - window_seconds:
            events.popleft()
        if len(events) >= limit:
            return events[0] + window_seconds - now
        events.append(now)
        return None
