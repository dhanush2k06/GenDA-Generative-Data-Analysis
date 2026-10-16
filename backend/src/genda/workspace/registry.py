"""
Central WorkspaceResourceRegistry.
Ensures every cache, in-memory DataFrame, DuckDB handle, and temp file
is strictly partitioned and registered by workspace ID.
"""

from __future__ import annotations
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Set, Optional


class WorkspaceResources:
    def __init__(self, workspace_id: bytes):
        self.workspace_id = workspace_id
        self.sessions: Dict[str, Any] = {}
        self.temp_files: Set[Path] = set()
        self.temp_dirs: Set[Path] = set()
        self.duckdb_connections: List[Any] = []
        self.caches: Dict[str, Any] = {}

    def clear(self) -> dict[str, int]:
        """Purge and dereference all resources in this workspace."""
        sessions_purged = len(self.sessions)
        for s in self.sessions.values():
            if hasattr(s, "clear"):
                s.clear()
        self.sessions.clear()

        # Close DuckDB handles
        db_closed = len(self.duckdb_connections)
        for conn in self.duckdb_connections:
            try:
                conn.close()
            except Exception:
                pass
        self.duckdb_connections.clear()

        # Delete temp files
        files_removed = 0
        for f in list(self.temp_files):
            try:
                if f.is_file() or f.is_symlink():
                    f.unlink(missing_ok=True)
                    files_removed += 1
            except Exception:
                pass
        self.temp_files.clear()

        # Delete temp dirs
        dirs_removed = 0
        for d in list(self.temp_dirs):
            try:
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
                    dirs_removed += 1
            except Exception:
                pass
        self.temp_dirs.clear()

        caches_cleared = len(self.caches)
        self.caches.clear()

        return {
            "sessions_purged": sessions_purged,
            "duckdb_closed": db_closed,
            "files_removed": files_removed,
            "dirs_removed": dirs_removed,
            "caches_cleared": caches_cleared,
        }


class WorkspaceResourceRegistry:
    """
    Thread-safe registry mapping workspace_id -> WorkspaceResources.
    """

    def __init__(self):
        self._workspaces: Dict[bytes, WorkspaceResources] = {}
        self._lock = threading.RLock()

    def _get_or_create(self, workspace_id: bytes) -> WorkspaceResources:
        if workspace_id not in self._workspaces:
            self._workspaces[workspace_id] = WorkspaceResources(workspace_id)
        return self._workspaces[workspace_id]

    def register_session(self, workspace_id: bytes, session_id: str, session_data: Any):
        with self._lock:
            ws = self._get_or_create(workspace_id)
            ws.sessions[session_id] = session_data

    def get_session(self, workspace_id: bytes, session_id: str) -> Optional[Any]:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return None
            return ws.sessions.get(session_id)

    def remove_session(self, workspace_id: bytes, session_id: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            session = ws.sessions.pop(session_id, None)
            if session and hasattr(session, "clear"):
                session.clear()
            return session is not None

    def register_temp_file(self, workspace_id: bytes, path: Path | str):
        with self._lock:
            ws = self._get_or_create(workspace_id)
            ws.temp_files.add(Path(path))

    def register_temp_dir(self, workspace_id: bytes, path: Path | str):
        with self._lock:
            ws = self._get_or_create(workspace_id)
            ws.temp_dirs.add(Path(path))

    def register_duckdb_conn(self, workspace_id: bytes, conn: Any):
        with self._lock:
            ws = self._get_or_create(workspace_id)
            ws.duckdb_connections.append(conn)

    def purge_workspace(self, workspace_id: bytes) -> dict[str, int]:
        with self._lock:
            ws = self._workspaces.pop(workspace_id, None)
            if ws:
                return ws.clear()
            return {
                "sessions_purged": 0,
                "duckdb_closed": 0,
                "files_removed": 0,
                "dirs_removed": 0,
                "caches_cleared": 0,
            }

    def has_workspace(self, workspace_id: bytes) -> bool:
        with self._lock:
            return workspace_id in self._workspaces


resource_registry = WorkspaceResourceRegistry()
