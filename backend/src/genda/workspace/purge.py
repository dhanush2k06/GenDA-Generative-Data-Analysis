"""
Purge state machine and post-purge verifier.
Implements the 8-step complete purge flow:
active -> revoking -> crypto-shred -> memory & cache purge -> db purge -> verification -> revoked.
"""

from __future__ import annotations
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from genda.db.models import (
    Workspace,
    Dataset,
    DatasetColumn,
    AnalysisRun,
    Recipe,
    RecipeOutcome,
    PurgeJob,
    utcnow,
)
from genda.workspace.registry import resource_registry
from genda.workspace.tasks import task_registry

logger = logging.getLogger("genda.workspace.purge")


class PurgeVerificationError(RuntimeError):
    """Raised when post-purge verification discovers residual data."""
    pass


def execute_workspace_purge(workspace_id: bytes, db: Session) -> Dict[str, Any]:
    """
    Executes the 8-step complete purge process for the given workspace_id.
    Returns a counts-only summary report.
    """
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise ValueError("Workspace not found.")

    report: Dict[str, Any] = {
        "workspace_id": workspace_id.hex(),
        "key_id": ws.key_id,
        "steps_completed": [],
    }

    # Step 1: Transition status to 'revoking'
    ws.status = "revoking"
    db.commit()
    report["steps_completed"].append("status_revoking")

    # Step 2: Cancel running tasks with timeout
    cancelled_tasks = task_registry.cancel_workspace_tasks(workspace_id, timeout_seconds=2.0)
    report["cancelled_tasks"] = cancelled_tasks
    report["steps_completed"].append("tasks_cancelled")

    # Step 3: Crypto-shredding: wipe wrapped_dek and key_verifier immediately
    ws.wrapped_dek = None
    ws.key_verifier = None
    db.commit()
    report["steps_completed"].append("crypto_shredded")

    # Step 4 & 5: Clear in-memory DataFrames, caches, DuckDB connections, temp files
    registry_stats = resource_registry.purge_workspace(workspace_id)
    report["registry_stats"] = registry_stats
    report["steps_completed"].append("in_memory_and_caches_purged")

    # Step 6: Purge all MySQL database records (cascading children)
    deleted_counts = {}

    deleted_counts["recipe_outcomes"] = (
        db.query(RecipeOutcome).filter(RecipeOutcome.workspace_id == workspace_id).delete(synchronize_session=False)
    )
    deleted_counts["recipes"] = (
        db.query(Recipe).filter(Recipe.workspace_id == workspace_id).delete(synchronize_session=False)
    )
    deleted_counts["analysis_runs"] = (
        db.query(AnalysisRun).filter(AnalysisRun.workspace_id == workspace_id).delete(synchronize_session=False)
    )
    deleted_counts["dataset_columns"] = (
        db.query(DatasetColumn).filter(DatasetColumn.workspace_id == workspace_id).delete(synchronize_session=False)
    )
    deleted_counts["datasets"] = (
        db.query(Dataset).filter(Dataset.workspace_id == workspace_id).delete(synchronize_session=False)
    )

    db.commit()
    report["deleted_db_rows"] = deleted_counts
    report["steps_completed"].append("database_rows_deleted")

    # Step 7: Post-purge verification
    residual_datasets = db.query(Dataset).filter(Dataset.workspace_id == workspace_id).count()
    residual_runs = db.query(AnalysisRun).filter(AnalysisRun.workspace_id == workspace_id).count()
    residual_recipes = db.query(Recipe).filter(Recipe.workspace_id == workspace_id).count()
    in_registry = resource_registry.has_workspace(workspace_id)

    if residual_datasets > 0 or residual_runs > 0 or residual_recipes > 0 or in_registry:
        raise PurgeVerificationError(
            f"Residual data detected after purge! Datasets={residual_datasets}, "
            f"Runs={residual_runs}, Recipes={residual_recipes}, RegistryActive={in_registry}"
        )
    report["steps_completed"].append("verification_passed")

    # Step 8: Update workspace tombstone to 'revoked'
    ws.status = "revoked"
    ws.revoked_at = utcnow()

    # Record or update purge_job entry
    job = db.query(PurgeJob).filter(PurgeJob.workspace_id == workspace_id).first()
    if not job:
        job = PurgeJob(
            workspace_id=workspace_id,
            status="completed",
            completed_steps=report["steps_completed"],
        )
        db.add(job)
    else:
        job.status = "completed"
        job.completed_steps = report["steps_completed"]
        job.updated_at = utcnow()

    db.commit()
    report["final_status"] = "revoked"
    return report
