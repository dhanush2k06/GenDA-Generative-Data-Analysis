"""
Repository for recording analysis runs scoped by WorkspaceContext.
Parameters are encrypted; versions and execution statistics are stored safely.
"""

from __future__ import annotations
import json
import secrets
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from genda.auth.context import WorkspaceContext
from genda.db.models import AnalysisRun, utcnow


class RunRepo:
    def __init__(self, db: Session):
        self.db = db

    def record_run(
        self,
        ctx: WorkspaceContext,
        dataset_id: bytes,
        operation: str,
        params: Dict[str, Any],
        validation_status: str,
        runtime_ms: int,
        library_versions: Dict[str, str],
        recipe_id: Optional[bytes] = None,
        run_id: Optional[bytes] = None,
    ) -> AnalysisRun:
        if run_id is None:
            run_id = secrets.token_bytes(16)

        params_json = json.dumps(params)
        params_enc = ctx.encrypt(
            plaintext=params_json,
            table="analysis_runs",
            column="params_enc",
            row_id=run_id,
        )

        run = AnalysisRun(
            workspace_id=ctx.workspace_id,
            id=run_id,
            dataset_id=dataset_id,
            recipe_id=recipe_id,
            operation=operation,
            params_enc=params_enc,
            validation_status=validation_status,
            runtime_ms=runtime_ms,
            library_versions=library_versions,
            created_at=utcnow(),
        )
        self.db.add(run)
        self.db.commit()
        return run

    def list_runs(
        self,
        ctx: WorkspaceContext,
        dataset_id: Optional[bytes] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(AnalysisRun).filter(AnalysisRun.workspace_id == ctx.workspace_id)
        if dataset_id:
            query = query.filter(AnalysisRun.dataset_id == dataset_id)

        runs = query.order_by(AnalysisRun.created_at.desc()).limit(min(limit, 100)).all()

        results = []
        for r in runs:
            params_json = ctx.decrypt_str(r.params_enc, table="analysis_runs", column="params_enc", row_id=r.id)
            results.append({
                "id": r.id.hex(),
                "dataset_id": r.dataset_id.hex(),
                "recipe_id": r.recipe_id.hex() if r.recipe_id else None,
                "operation": r.operation,
                "params": json.loads(params_json),
                "validation_status": r.validation_status,
                "runtime_ms": r.runtime_ms,
                "library_versions": r.library_versions,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return results
