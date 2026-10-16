"""
Repository for dataset metadata storage, scoped strictly by WorkspaceContext.
Enforces data classification: never stores raw rows or individual cell samples.
Filters categorical statistics to minimum-count thresholds to prevent leakage.
"""

from __future__ import annotations
import json
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from genda.auth.context import WorkspaceContext
from genda.db.models import Dataset, DatasetColumn, utcnow

MIN_CATEGORICAL_COUNT = 5


def filter_profile_for_storage(profile_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize profile dict before persistence:
    1. Strip any raw samples or cell values.
    2. Filter categorical frequencies below MIN_CATEGORICAL_COUNT to prevent data leakage.
    """
    clean_profile = json.loads(json.dumps(profile_dict))  # Deep copy

    # Remove any potential raw preview or sample data
    clean_profile.pop("samples", None)
    clean_profile.pop("preview_rows", None)
    clean_profile.pop("raw_values", None)

    # Sanitize column frequencies
    columns = clean_profile.get("columns", [])
    for col in columns:
        col.pop("sample_values", None)
        frequencies = col.get("frequencies")
        if isinstance(frequencies, dict):
            filtered_freq = {}
            suppressed_count = 0
            for val, count in frequencies.items():
                if count >= MIN_CATEGORICAL_COUNT:
                    filtered_freq[str(val)] = count
                else:
                    suppressed_count += count
            if suppressed_count > 0:
                filtered_freq["<other_below_threshold>"] = suppressed_count
            col["frequencies"] = filtered_freq

    return clean_profile


class DatasetRepo:
    def __init__(self, db: Session):
        self.db = db

    def save_dataset(
        self,
        ctx: WorkspaceContext,
        dataset_name: str,
        fingerprint: bytes,
        row_count: int,
        col_count: int,
        profile_dict: Dict[str, Any],
        columns_data: List[Dict[str, Any]],
        dataset_id: Optional[bytes] = None,
    ) -> Dataset:
        """
        Persists dataset metadata and column definitions.
        All sensitive columns (name, profile, column names) are encrypted with DEK.
        """
        if dataset_id is None:
            dataset_id = secrets.token_bytes(16)

        sanitized_profile = filter_profile_for_storage(profile_dict)
        profile_json = json.dumps(sanitized_profile)

        # Context-bound encryption
        name_enc = ctx.encrypt(
            plaintext=dataset_name,
            table="datasets",
            column="name_enc",
            row_id=dataset_id,
        )
        profile_enc = ctx.encrypt(
            plaintext=profile_json,
            table="datasets",
            column="profile_enc",
            row_id=dataset_id,
        )

        dataset = Dataset(
            workspace_id=ctx.workspace_id,
            id=dataset_id,
            fingerprint=fingerprint,
            name_enc=name_enc,
            row_count=row_count,
            col_count=col_count,
            profile_enc=profile_enc,
            created_at=utcnow(),
        )
        self.db.add(dataset)

        # Add column definitions
        for idx, col in enumerate(columns_data):
            col_id = secrets.token_bytes(16)
            col_name = str(col.get("name", f"col_{idx}"))
            col_name_hash = hashlib.sha256(col_name.encode("utf-8")).digest()
            col_name_enc = ctx.encrypt(
                plaintext=col_name,
                table="dataset_columns",
                column="name_enc",
                row_id=col_id,
            )

            ds_col = DatasetColumn(
                workspace_id=ctx.workspace_id,
                id=col_id,
                dataset_id=dataset_id,
                col_index=idx,
                name_enc=col_name_enc,
                name_hash=col_name_hash,
                type_class=str(col.get("type_class", "unknown")),
                null_rate_bucket=str(col.get("null_rate_bucket", "none")),
                distinct_ratio_bucket=str(col.get("distinct_ratio_bucket", "low")),
                skew_bucket=str(col.get("skew_bucket", "normal")),
            )
            self.db.add(ds_col)

        self.db.commit()
        return dataset

    def get_dataset(self, ctx: WorkspaceContext, dataset_id: bytes) -> Optional[Dict[str, Any]]:
        """Fetch and decrypt a dataset's metadata."""
        ds = (
            self.db.query(Dataset)
            .filter(Dataset.workspace_id == ctx.workspace_id, Dataset.id == dataset_id)
            .first()
        )
        if not ds:
            return None

        # Decrypt fields
        name = ctx.decrypt_str(ds.name_enc, table="datasets", column="name_enc", row_id=ds.id)
        profile_json = ctx.decrypt_str(ds.profile_enc, table="datasets", column="profile_enc", row_id=ds.id)
        profile = json.loads(profile_json)

        # Fetch columns
        columns = (
            self.db.query(DatasetColumn)
            .filter(DatasetColumn.workspace_id == ctx.workspace_id, DatasetColumn.dataset_id == ds.id)
            .order_by(DatasetColumn.col_index.asc())
            .all()
        )

        decrypted_cols = []
        for c in columns:
            col_name = ctx.decrypt_str(c.name_enc, table="dataset_columns", column="name_enc", row_id=c.id)
            decrypted_cols.append({
                "id": c.id.hex(),
                "col_index": c.col_index,
                "name": col_name,
                "type_class": c.type_class,
                "null_rate_bucket": c.null_rate_bucket,
                "distinct_ratio_bucket": c.distinct_ratio_bucket,
                "skew_bucket": c.skew_bucket,
            })

        return {
            "id": ds.id.hex(),
            "fingerprint": ds.fingerprint.hex(),
            "name": name,
            "row_count": ds.row_count,
            "col_count": ds.col_count,
            "profile": profile,
            "columns": decrypted_cols,
            "created_at": ds.created_at.isoformat() if ds.created_at else None,
        }

    def list_datasets(self, ctx: WorkspaceContext, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List datasets metadata summaries for the workspace."""
        results = (
            self.db.query(Dataset)
            .filter(Dataset.workspace_id == ctx.workspace_id)
            .order_by(Dataset.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
            .all()
        )

        items = []
        for ds in results:
            name = ctx.decrypt_str(ds.name_enc, table="datasets", column="name_enc", row_id=ds.id)
            items.append({
                "id": ds.id.hex(),
                "name": name,
                "fingerprint": ds.fingerprint.hex(),
                "row_count": ds.row_count,
                "col_count": ds.col_count,
                "created_at": ds.created_at.isoformat() if ds.created_at else None,
            })
        return items

    def delete_dataset(self, ctx: WorkspaceContext, dataset_id: bytes) -> bool:
        """Delete a dataset and its cascading child records."""
        deleted = (
            self.db.query(Dataset)
            .filter(Dataset.workspace_id == ctx.workspace_id, Dataset.id == dataset_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted > 0
