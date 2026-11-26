"""Small in-memory rate limiters. The free Gemini tier allows ~15 requests a minute, and one chat message
uses 2 to 3 model calls, so /chat is limited per visitor AND globally, and wrong logins are locked out."""
import threading
import time
from collections import defaultdict, deque


class SlidingWindow:
    """Allow at most `limit` hits per `window` seconds for each key."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        """Record a hit. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False, max(1, int(self.window - (now - q[0])) + 1)
            q.append(now)
            return True, 0

    def reset(self):
        with self._lock:
            self._hits.clear()


class FailureLockout:
    """Lock a key out for `lockout` seconds after `max_failures` failures inside `window` seconds."""

    def __init__(self, max_failures: int = 5, window: float = 900, lockout: float = 900):
        self.max_failures, self.window, self.lockout = max_failures, window, lockout
        self._fails: dict[str, deque] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def blocked_for(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            until = self._locked_until.get(key, 0)
            if until > now:
                return int(until - now) + 1
            self._locked_until.pop(key, None)
            return 0

    def fail(self, key: str):
        now = time.monotonic()
        with self._lock:
            q = self._fails[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            q.append(now)
            if len(q) >= self.max_failures:
                self._locked_until[key] = now + self.lockout
                q.clear()

    def success(self, key: str):
        with self._lock:
            self._fails.pop(key, None)
            self._locked_until.pop(key, None)
