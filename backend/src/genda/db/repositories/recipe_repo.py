"""
Repository for reusable analysis recipes and outcome tracking.
Recipes are strictly structured JSON specifications using column roles;
no executable code or SQL is ever stored.
"""

from __future__ import annotations
import json
import secrets
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from genda.auth.context import WorkspaceContext
from genda.db.models import Recipe, RecipeOutcome, utcnow


class RecipeRepo:
    def __init__(self, db: Session):
        self.db = db

    def save_recipe(
        self,
        ctx: WorkspaceContext,
        name: str,
        category: str,
        spec: Dict[str, Any],
        description: str = "",
        version: str = "1.0",
        recipe_id: Optional[bytes] = None,
    ) -> Recipe:
        """
        Saves a structured analytical recipe.
        Name, description, and spec_json are encrypted using WorkspaceContext.
        """
        if recipe_id is None:
            recipe_id = secrets.token_bytes(16)

        spec_json = json.dumps(spec)
        name_enc = ctx.encrypt(name, table="recipes", column="name_enc", row_id=recipe_id)
        desc_enc = ctx.encrypt(description, table="recipes", column="description_enc", row_id=recipe_id)
        spec_enc = ctx.encrypt(spec_json, table="recipes", column="spec_json_enc", row_id=recipe_id)

        recipe = Recipe(
            workspace_id=ctx.workspace_id,
            id=recipe_id,
            name_enc=name_enc,
            description_enc=desc_enc,
            spec_json_enc=spec_enc,
            category=category,
            version=version,
            created_at=utcnow(),
        )
        self.db.add(recipe)
        self.db.commit()
        return recipe

    def get_recipe(self, ctx: WorkspaceContext, recipe_id: bytes) -> Optional[Dict[str, Any]]:
        recipe = (
            self.db.query(Recipe)
            .filter(Recipe.workspace_id == ctx.workspace_id, Recipe.id == recipe_id)
            .first()
        )
        if not recipe:
            return None

        name = ctx.decrypt_str(recipe.name_enc, table="recipes", column="name_enc", row_id=recipe.id)
        desc = ctx.decrypt_str(recipe.description_enc, table="recipes", column="description_enc", row_id=recipe.id)
        spec_json = ctx.decrypt_str(recipe.spec_json_enc, table="recipes", column="spec_json_enc", row_id=recipe.id)

        return {
            "id": recipe.id.hex(),
            "name": name,
            "description": desc,
            "category": recipe.category,
            "version": recipe.version,
            "spec": json.loads(spec_json),
            "created_at": recipe.created_at.isoformat() if recipe.created_at else None,
        }

    def list_recipes(
        self,
        ctx: WorkspaceContext,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Recipe).filter(Recipe.workspace_id == ctx.workspace_id)
        if category:
            query = query.filter(Recipe.category == category)

        recipes = query.order_by(Recipe.created_at.desc()).limit(min(limit, 100)).all()

        results = []
        for r in recipes:
            name = ctx.decrypt_str(r.name_enc, table="recipes", column="name_enc", row_id=r.id)
            desc = ctx.decrypt_str(r.description_enc, table="recipes", column="description_enc", row_id=r.id)
            spec_json = ctx.decrypt_str(r.spec_json_enc, table="recipes", column="spec_json_enc", row_id=r.id)
            results.append({
                "id": r.id.hex(),
                "name": name,
                "description": desc,
                "category": r.category,
                "version": r.version,
                "spec": json.loads(spec_json),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return results

    def record_outcome(
        self,
        ctx: WorkspaceContext,
        recipe_id: bytes,
        dataset_id: bytes,
        validation_status: str,
        baseline_delta: Dict[str, Any],
        feedback: Optional[str] = None,
    ) -> RecipeOutcome:
        outcome_id = secrets.token_bytes(16)
        outcome = RecipeOutcome(
            workspace_id=ctx.workspace_id,
            id=outcome_id,
            recipe_id=recipe_id,
            dataset_id=dataset_id,
            validation_status=validation_status,
            baseline_delta_json=baseline_delta,
            feedback=feedback,
            created_at=utcnow(),
        )
        self.db.add(outcome)
        self.db.commit()
        return outcome
