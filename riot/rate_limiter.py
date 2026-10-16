"""Sliding-window rate limiter for the Riot API.

Riot enforces several limits at once (e.g. 20 per 1 s AND 100 per 120 s),
separately per routing value (euw1, europe, ...) and per method. Every bucket
here is identified by a key such as "europe" or "europe:match", and holds one
window per (limit, seconds) pair.
"""
import threading
import time
from collections import deque


def safe_limit(limit):
    """Stay a bit below Riot's limit: 20 -> 18, 100 -> 95."""
    return max(1, limit - max(2, limit // 20))


def parse_limit_header(value):
    """'20:1,100:120' -> [(20, 1), (100, 120)]"""
    pairs = []
    for part in value.split(","):
        amount, seconds = part.strip().split(":")
        pairs.append((int(amount), int(seconds)))
    return pairs


class _Window:
    def __init__(self, limit, seconds):
        self.limit = limit
        self.seconds = seconds
        self.stamps = deque()

    def prune(self, now):
        while self.stamps and self.stamps[0] <= now - self.seconds:
            self.stamps.popleft()

    def wait_time(self, now):
        self.prune(now)
        if len(self.stamps) < safe_limit(self.limit):
            return 0.0
        # Wait until the oldest request that keeps us at the limit expires.
        index = len(self.stamps) - safe_limit(self.limit)
        return self.stamps[index] + self.seconds - now


class RateLimiter:
    def __init__(self, clock=time.monotonic, sleep=time.sleep):
        self._clock = clock
        self._sleep = sleep
        self._buckets = {}
        self._lock = threading.Lock()

    def set_limits(self, key, limits):
        """Set the (limit, seconds) windows of a bucket, keeping history."""
        with self._lock:
            old = {w.seconds: w for w in self._buckets.get(key, [])}
            windows = []
            for limit, seconds in limits:
                window = old.get(seconds) or _Window(limit, seconds)
                window.limit = limit
                windows.append(window)
            self._buckets[key] = windows

    def has_limits(self, key):
        return key in self._buckets

    def acquire(self, *keys):
        """Block until a request is allowed in every given bucket, then record it."""
        while True:
            with self._lock:
                now = self._clock()
                wait = max(
                    (w.wait_time(now) for key in keys for w in self._buckets.get(key, [])),
                    default=0.0,
                )
                if wait <= 0:
                    for key in keys:
                        for window in self._buckets.get(key, []):
                            window.stamps.append(now)
                    return
            self._sleep(wait)

    def sync_counts(self, key, counts):
        """Apply Riot's X-*-Rate-Limit-Count header ([(count, seconds), ...]).

        If Riot counted more requests than we did (another script using the same
        key, or a restart), pad the window so we slow down accordingly.
        """
        with self._lock:
            now = self._clock()
            for count, seconds in counts:
                for window in self._buckets.get(key, []):
                    if window.seconds != seconds:
                        continue
                    window.prune(now)
                    while len(window.stamps) < count:
                        window.stamps.append(now)
