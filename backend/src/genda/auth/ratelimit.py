"""
Rate limiting and temporary lockout protection for workspace key authentication attempts.
Protects against online brute-force guessing of key IDs and secrets.
"""

from __future__ import annotations
import time
import threading


class KeyRateLimiter:
    """
    Tracks failed authentication attempts per key_id.
    Enforces a temporary lockout when failed attempts exceed max_attempts within window_seconds.
    """

    def __init__(self, max_attempts: int = 5, lockout_seconds: float = 60.0):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, list[float]] = {}
        self._lockouts: dict[str, float] = {}
        self._lock = threading.Lock()

    def is_locked(self, key_id: str) -> bool:
        """Check if the key_id is currently locked out."""
        with self._lock:
            now = time.time()
            unlock_time = self._lockouts.get(key_id)
            if unlock_time:
                if now < unlock_time:
                    return True
                else:
                    # Lockout expired
                    del self._lockouts[key_id]
                    self._failures.pop(key_id, None)
            return False

    def get_remaining_lockout_seconds(self, key_id: str) -> float:
        """Get remaining lockout seconds for key_id."""
        with self._lock:
            now = time.time()
            unlock_time = self._lockouts.get(key_id, 0.0)
            return max(0.0, unlock_time - now)

    def record_failure(self, key_id: str) -> bool:
        """
        Record a failed authentication attempt.
        Returns True if this failure triggered a new lockout.
        """
        with self._lock:
            now = time.time()
            # Clean old timestamps (> 5 minutes old)
            timestamps = [t for t in self._failures.get(key_id, []) if now - t < 300.0]
            timestamps.append(now)
            self._failures[key_id] = timestamps

            if len(timestamps) >= self.max_attempts:
                self._lockouts[key_id] = now + self.lockout_seconds
                return True
            return False

    def record_success(self, key_id: str):
        """Clear failure counts upon successful authentication."""
        with self._lock:
            self._failures.pop(key_id, None)
            self._lockouts.pop(key_id, None)

    def reset(self):
        """Reset all rate limiting state (useful for tests)."""
        with self._lock:
            self._failures.clear()
            self._lockouts.clear()


key_rate_limiter = KeyRateLimiter()
