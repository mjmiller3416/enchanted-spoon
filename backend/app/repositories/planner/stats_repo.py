"""app/repositories/planner/stats_repo.py

Repository for planner statistics and batch operations.
Handles counting, statistics, batch updates, and position normalization.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import List

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, joinedload

from ...models.meal import Meal
from ...models.planner_entry import PlannerEntry


# ── Constants ───────────────────────────────────────────────────────────────────────────────────────────────
MAX_PLANNER_ENTRIES = 20


# ── Planner Stats Repository ────────────────────────────────────────────────────────────────────────────────
class PlannerStatsRepo:
    """Repository for planner statistics and batch operations."""

    def __init__(self, session: Session):
        """Initialize the Planner Stats Repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # ── Count and Statistics Operations ─────────────────────────────────────────────────────────────────────
    def count(self, user_id: int) -> int:
        """
        Count total number of active planner entries (excludes cleared) for a user.

        Args:
            user_id: ID of the user whose entries to count

        Returns:
            Total count of active entries belonging to the user
        """
        stmt = (
            select(func.count())
            .select_from(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_cleared == False)
        )
        return self.session.execute(stmt).scalar() or 0

    def count_incomplete(self, user_id: int) -> int:
        """
        Count incomplete planner entries (excludes completed and cleared) for a user.
        Used for capacity checks — completed entries awaiting "Clear completed"
        don't consume planner capacity.

        Args:
            user_id: ID of the user whose incomplete entries to count

        Returns:
            Count of incomplete, non-cleared entries belonging to the user
        """
        stmt = (
            select(func.count())
            .select_from(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_completed == False)
            .where(PlannerEntry.is_cleared == False)
        )
        return self.session.execute(stmt).scalar() or 0

    def count_completed(self, user_id: int) -> int:
        """
        Count completed planner entries for a user.

        Args:
            user_id: ID of the user whose completed entries to count

        Returns:
            Count of completed entries belonging to the user
        """
        stmt = (
            select(func.count())
            .select_from(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_completed == True)
        )
        return self.session.execute(stmt).scalar() or 0

    def count_active_entries_for_meal(self, meal_id: int, user_id: int) -> int:
        """
        Count active (non-cleared) planner entries for a specific meal belonging to a user.
        Used for transient meal cleanup logic.

        Args:
            meal_id: ID of the meal
            user_id: ID of the user whose entries to count

        Returns:
            Count of active entries referencing this meal belonging to the user
        """
        stmt = (
            select(func.count())
            .select_from(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.meal_id == meal_id)
            .where(PlannerEntry.is_cleared == False)
        )
        return self.session.execute(stmt).scalar() or 0

    def count_all_entries_for_meal(self, meal_id: int, user_id: int) -> int:
        """
        Count all planner entries (active + cleared) for a specific meal belonging to a user.
        Used to preserve cooking history when cleaning up transient meals.

        Args:
            meal_id: ID of the meal
            user_id: ID of the user whose entries to count

        Returns:
            Count of all entries (including cleared) referencing this meal belonging to the user
        """
        stmt = (
            select(func.count())
            .select_from(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.meal_id == meal_id)
        )
        return self.session.execute(stmt).scalar() or 0

    def get_completion_stats_for_meal(self, meal_id: int, user_id: int) -> dict:
        """
        Get completion statistics for a specific meal belonging to a user.

        Args:
            meal_id: ID of the meal
            user_id: ID of the user whose stats to get

        Returns:
            dict with 'times_cooked' (int) and 'last_cooked' (datetime or None)
        """
        stmt = (
            select(
                func.count(PlannerEntry.id).label('times_cooked'),
                func.max(PlannerEntry.completed_at).label('last_cooked')
            )
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.meal_id == meal_id)
            .where(PlannerEntry.is_completed == True)
        )
        result = self.session.execute(stmt).first()
        return {
            'times_cooked': result.times_cooked or 0,
            'last_cooked': result.last_cooked
        }

    def is_at_capacity(self, user_id: int) -> bool:
        """
        Check if the planner is at maximum capacity for a user.
        Only incomplete entries count — completed meals awaiting clear don't
        consume capacity.

        Args:
            user_id: ID of the user whose planner to check

        Returns:
            True if at capacity (MAX_PLANNER_ENTRIES incomplete entries)
        """
        return self.count_incomplete(user_id) >= MAX_PLANNER_ENTRIES

    # ── Batch Update Operations ─────────────────────────────────────────────────────────────────────────────
    def reorder_entries(self, entry_ids: List[int], user_id: int) -> bool:
        """
        Reorder entries based on the provided ID order for a specific user.
        Sets positions to 0, 1, 2, ... based on ID order.

        Args:
            entry_ids: List of entry IDs in desired order
            user_id: ID of the user who owns the entries

        Returns:
            True if successful
        """
        for position, entry_id in enumerate(entry_ids):
            stmt = (
                update(PlannerEntry)
                .where(PlannerEntry.id == entry_id)
                .where(PlannerEntry.user_id == user_id)
                .values(position=position)
            )
            self.session.execute(stmt)
        self.session.flush()
        return True

    # ── Batch Delete Operations ─────────────────────────────────────────────────────────────────────────────
    def remove_entries_by_meal_id(self, meal_id: int, user_id: int) -> int:
        """
        Remove all planner entries for a specific meal belonging to a user.

        Args:
            meal_id: ID of the meal
            user_id: ID of the user whose entries to remove

        Returns:
            Number of entries removed
        """
        stmt = (
            delete(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.meal_id == meal_id)
        )
        result = self.session.execute(stmt)
        self.session.flush()
        self._normalize_positions(user_id)
        return result.rowcount

    def clear_all(self, user_id: int) -> int:
        """
        Clear all planner entries for a specific user.

        Args:
            user_id: ID of the user whose entries to clear

        Returns:
            Number of entries cleared
        """
        stmt = delete(PlannerEntry).where(PlannerEntry.user_id == user_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def clear_completed(self, user_id: int) -> int:
        """
        Soft-delete all completed planner entries by marking them as cleared for a user.
        Preserves cooking history for streak calculation.

        Args:
            user_id: ID of the user whose completed entries to clear

        Returns:
            Number of entries cleared
        """
        stmt = (
            update(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_completed == True)
            .where(PlannerEntry.is_cleared == False)
            .values(is_cleared=True)
        )
        result = self.session.execute(stmt)
        self.session.flush()
        self._normalize_positions(user_id)
        return result.rowcount

    # ── Utility Methods ─────────────────────────────────────────────────────────────────────────────────────
    def _normalize_positions(self, user_id: int) -> None:
        """
        Normalize positions to be contiguous (0, 1, 2, ...) for a user.
        Called after deletions to prevent gaps.

        Args:
            user_id: ID of the user whose positions to normalize
        """
        # Get all active entries in position order
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.user_id == user_id)
            .where(PlannerEntry.is_cleared == False)
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
            .order_by(PlannerEntry.position)
        )
        result = self.session.execute(stmt)
        entries = result.scalars().unique().all()

        for i, entry in enumerate(entries):
            if entry.position != i:
                entry.position = i
        self.session.flush()
