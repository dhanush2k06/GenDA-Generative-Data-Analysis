"""
Task registry for in-flight analysis tasks with cancellation tokens.
Ensures running tasks can be cleanly stopped when a workspace key is revoked.
"""

from __future__ import annotations
import threading
import time
from typing import Dict, Set


class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self):
        if self._event.is_set():
            raise InterruptedError("Operation was cancelled due to workspace revocation.")


class TaskRegistry:
    def __init__(self):
        self._tasks: Dict[bytes, Set[CancellationToken]] = {}
        self._lock = threading.Lock()

    def register_task(self, workspace_id: bytes) -> CancellationToken:
        token = CancellationToken()
        with self._lock:
            if workspace_id not in self._tasks:
                self._tasks[workspace_id] = set()
            self._tasks[workspace_id].add(token)
        return token

    def unregister_task(self, workspace_id: bytes, token: CancellationToken):
        with self._lock:
            tasks = self._tasks.get(workspace_id)
            if tasks:
                tasks.discard(token)
                if not tasks:
                    del self._tasks[workspace_id]

    def cancel_workspace_tasks(self, workspace_id: bytes, timeout_seconds: float = 3.0) -> int:
        """
        Signals cancellation to all in-flight tasks for this workspace
        and waits up to timeout_seconds for them to register cancellation.
        """
        with self._lock:
            tasks = list(self._tasks.get(workspace_id, []))

        cancelled_count = len(tasks)
        for token in tasks:
            token.cancel()

        # Wait briefly for tasks to exit
        start = time.time()
        while time.time() - start < timeout_seconds:
            with self._lock:
                remaining = self._tasks.get(workspace_id)
                if not remaining:
                    break
            time.sleep(0.05)

        return cancelled_count


task_registry = TaskRegistry()
