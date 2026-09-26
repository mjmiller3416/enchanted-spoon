"""app/repositories/planner/query_repo.py

Repository for planner query and retrieval operations.
Handles multi-entry queries for various filtering scenarios.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...models.meal import Meal
from ...models.planner_entry import PlannerEntry


# ── Planner Query Repository ────────────────────────────────────────────────────────────────────────────────
class PlannerQueryRepo:
    """Repository for planner query and retrieval operations."""

    def __init__(self, session: Session):
        """Initialize the Planner Query Repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # ── Query Operations ────────────────────────────────────────────────────────────────────────────────────
    def get_all(self, user_id: int) -> List[PlannerEntry]:
        """
        Get all active planner entries ordered by position, with eager-loaded relationships.
        Excludes cleared entries.

        Args:
            user_id: ID of the user whose planner entries to retrieve

        Returns:
            List of all active planner entries belonging to the user
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_cleared == False)
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
            .order_by(PlannerEntry.position, PlannerEntry.id)
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_by_meal_id(self, meal_id: int, user_id: int) -> List[PlannerEntry]:
        """
        Get all planner entries for a specific meal belonging to a user.

        Args:
            meal_id: ID of the meal
            user_id: ID of the user whose entries to retrieve

        Returns:
            List of planner entries for this meal belonging to the user
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.meal_id == meal_id)
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
            .order_by(PlannerEntry.position, PlannerEntry.id)
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_meal_ids(self, user_id: int) -> List[int]:
        """
        Get all meal IDs currently in the planner for a specific user.

        Args:
            user_id: ID of the user whose meal IDs to retrieve

        Returns:
            List of meal IDs in position order belonging to the user
        """
        stmt = (
            select(PlannerEntry.meal_id)
            .where(PlannerEntry.user_id == user_id)
            .order_by(PlannerEntry.position, PlannerEntry.id)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_completed_entries(self, user_id: int) -> List[PlannerEntry]:
        """
        Get all completed planner entries that haven't been cleared for a specific user.
        Used for the completed dropdown UI.

        Args:
            user_id: ID of the user whose completed entries to retrieve

        Returns:
            List of completed entries (excludes cleared) belonging to the user
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_completed == True)
            .where(PlannerEntry.is_cleared == False)
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
            .order_by(PlannerEntry.position, PlannerEntry.id)
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_cooking_history_entries(self, user_id: int) -> List[PlannerEntry]:
        """
        Get all entries with completion history for streak calculation for a specific user.
        Includes cleared entries to preserve cooking history.

        Args:
            user_id: ID of the user whose cooking history to retrieve

        Returns:
            List of all entries that have ever been completed belonging to the user
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.completed_at.isnot(None))
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_incomplete_entries(self, user_id: int) -> List[PlannerEntry]:
        """
        Get all incomplete planner entries that haven't been cleared for a specific user.

        Args:
            user_id: ID of the user whose incomplete entries to retrieve

        Returns:
            List of incomplete entries (excludes cleared) belonging to the user
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_completed == False)
            .where(PlannerEntry.is_cleared == False)
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
            .order_by(PlannerEntry.position, PlannerEntry.id)
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_shopping_entries(self, user_id: int) -> List[PlannerEntry]:
        """
        Get incomplete planner entries that have any shopping mode except 'none' for a user.

        Args:
            user_id: ID of the user whose shopping entries to retrieve

        Returns:
            List of entries to include in shopping list generation belonging to the user
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_completed == False)
            .where(PlannerEntry.is_cleared == False)
            .where(PlannerEntry.shopping_mode != 'none')
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
            .order_by(PlannerEntry.position, PlannerEntry.id)
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()
