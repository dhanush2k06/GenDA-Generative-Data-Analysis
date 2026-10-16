"""
In-memory session store with TTL expiry and explicit deletion.
Strictly local: dataframe and calculations reside in RAM only.
"""

from __future__ import annotations
import time
import secrets
import threading
from typing import Any
import polars as pl

from genda.core.models import AnalysisResult, DatasetProfile, SessionInfo


class SessionData:
    def __init__(self, session_id: str, df: pl.DataFrame, filename: str, workspace_id: bytes | None = None):
        self.session_id = session_id
        self.df = df
        self.filename = filename
        self.workspace_id = workspace_id
        self.created_at = time.time()
        self.last_accessed_at = time.time()
        self.profile: DatasetProfile | None = None
        self.results: list[AnalysisResult] = []

    def touch(self):
        self.last_accessed_at = time.time()

    def clear(self):
        """Explicitly dereference all dataframes and cached results."""
        self.df = pl.DataFrame()
        self.profile = None
        self.results.clear()


class SessionStore:
    def __init__(self, default_ttl_seconds: float = 3600.0):
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = default_ttl_seconds

    def create_session(self, df: pl.DataFrame, filename: str, workspace_id: bytes | None = None) -> str:
        with self._lock:
            self.purge_expired()
            session_id = secrets.token_hex(16)
            data = SessionData(session_id, df, filename, workspace_id=workspace_id)
            self._sessions[session_id] = data

            if workspace_id:
                from genda.workspace.registry import resource_registry
                resource_registry.register_session(workspace_id, session_id, data)

            return session_id

    def get_session(self, session_id: str) -> SessionData | None:
        with self._lock:
            data = self._sessions.get(session_id)
            if data is None:
                return None
            if time.time() - data.last_accessed_at > self._ttl_seconds:
                # Expired
                data.clear()
                del self._sessions[session_id]
                return None
            data.touch()
            return data

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            data = self._sessions.pop(session_id, None)
            if data is not None:
                if data.workspace_id:
                    from genda.workspace.registry import resource_registry
                    resource_registry.remove_session(data.workspace_id, session_id)
                data.clear()
                return True
            return False

    def delete_sessions_for_workspace(self, workspace_id: bytes) -> int:
        with self._lock:
            to_delete = [
                sid for sid, s in self._sessions.items()
                if s.workspace_id == workspace_id
            ]
            for sid in to_delete:
                s = self._sessions.pop(sid, None)
                if s:
                    s.clear()
            return len(to_delete)


    def clear_all(self):
        with self._lock:
            for s in self._sessions.values():
                s.clear()
            self._sessions.clear()

    def purge_expired(self):
        now = time.time()
        expired_keys = [
            sid for sid, s in self._sessions.items()
            if (now - s.last_accessed_at) > self._ttl_seconds
        ]
        for sid in expired_keys:
            s = self._sessions.pop(sid, None)
            if s:
                s.clear()

    def get_session_info(self, session_id: str) -> SessionInfo | None:
        with self._lock:
            s = self.get_session(session_id)
            if s is None:
                return None
            return SessionInfo(
                session_id=s.session_id,
                created_at=s.created_at,
                filename=s.filename,
                row_count=s.df.height,
                col_count=s.df.width,
                operations_count=len(s.results),
                expires_in_seconds=max(0.0, self._ttl_seconds - (time.time() - s.last_accessed_at)),
            )

    @property
    def active_count(self) -> int:
        with self._lock:
            self.purge_expired()
            return len(self._sessions)


# Global singleton instance
session_store = SessionStore()
