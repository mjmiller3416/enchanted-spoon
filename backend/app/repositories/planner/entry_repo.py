"""app/repositories/planner/entry_repo.py

Repository for individual planner entry CRUD operations.
Handles single-entry operations: create, read, update, delete.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ...models.meal import Meal
from ...models.planner_entry import PlannerEntry


# ── Planner Entry Repository ────────────────────────────────────────────────────────────────────────────────
class PlannerEntryRepo:
    """Repository for individual planner entry CRUD operations."""

    def __init__(self, session: Session):
        """Initialize the Planner Entry Repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # ── Create Operations ───────────────────────────────────────────────────────────────────────────────────
    def add_entry(self, meal_id: int, user_id: int, position: Optional[int] = None) -> PlannerEntry:
        """
        Add a meal to the planner for a specific user.

        Args:
            meal_id: ID of the meal to add
            user_id: ID of the user who owns this planner entry
            position: Optional position (defaults to next available)

        Returns:
            Created PlannerEntry
        """
        if position is None:
            position = self._get_next_position(user_id)

        entry = PlannerEntry(meal_id=meal_id, position=position, user_id=user_id)
        self.session.add(entry)
        self.session.flush()
        self.session.refresh(entry)
        return entry

    # ── Read Operations ─────────────────────────────────────────────────────────────────────────────────────
    def get_by_id(self, entry_id: int, user_id: Optional[int] = None) -> Optional[PlannerEntry]:
        """
        Get a planner entry by ID with eager-loaded meal and recipe.

        Args:
            entry_id: ID of the entry
            user_id: If provided, only return the entry if it belongs to this user.
                Returns None if the entry exists but belongs to a different user (no existence leak).

        Returns:
            PlannerEntry if found and owned by user, None otherwise
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.id == entry_id)
            .options(
                joinedload(PlannerEntry.meal).joinedload(Meal.main_recipe)
            )
        )
        if user_id is not None:
            stmt = stmt.where(PlannerEntry.user_id == user_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Update Operations ───────────────────────────────────────────────────────────────────────────────────
    def update(self, entry: PlannerEntry) -> PlannerEntry:
        """
        Update a planner entry.

        Args:
            entry: PlannerEntry with changes

        Returns:
            Updated entry
        """
        merged = self.session.merge(entry)
        self.session.flush()
        return merged

    def update_position(self, entry_id: int, new_position: int, user_id: int) -> Optional[PlannerEntry]:
        """
        Update the position of a planner entry if owned by the user.

        Args:
            entry_id: ID of the entry
            new_position: New position value
            user_id: ID of the user who owns the entry

        Returns:
            Updated entry or None if not found/not owned
        """
        entry = self.get_by_id(entry_id, user_id)
        if not entry:
            return None

        entry.position = new_position
        self.session.flush()
        return entry

    def mark_completed(self, entry_id: int, user_id: int) -> Optional[PlannerEntry]:
        """
        Mark a planner entry as completed if owned by the user.

        Args:
            entry_id: ID of the entry
            user_id: ID of the user who owns the entry

        Returns:
            Updated entry or None if not found/not owned
        """
        entry = self.get_by_id(entry_id, user_id)
        if not entry:
            return None

        entry.mark_completed()
        self.session.flush()
        return entry

    def mark_incomplete(self, entry_id: int, user_id: int) -> Optional[PlannerEntry]:
        """
        Mark a planner entry as incomplete if owned by the user.

        Args:
            entry_id: ID of the entry
            user_id: ID of the user who owns the entry

        Returns:
            Updated entry or None if not found/not owned
        """
        entry = self.get_by_id(entry_id, user_id)
        if not entry:
            return None

        entry.mark_incomplete()
        self.session.flush()
        return entry

    def cycle_shopping_mode(self, entry_id: int, user_id: int) -> Optional[PlannerEntry]:
        """
        Cycle the shopping mode of a planner entry if owned by the user: all -> produce_only -> none -> all.

        Locks the row for the duration of the transaction so that rapid repeated
        toggles (e.g. a user double-clicking) are serialized instead of racing on a
        stale read of shopping_mode, which would otherwise cause a lost update.

        Args:
            entry_id: ID of the entry
            user_id: ID of the user who owns the entry

        Returns:
            Updated entry or None if not found/not owned
        """
        stmt = (
            select(PlannerEntry)
            .where(PlannerEntry.id == entry_id, PlannerEntry.user_id == user_id)
            .with_for_update()
        )
        entry = self.session.execute(stmt).scalar_one_or_none()
        if not entry:
            return None

        entry.cycle_shopping_mode()
        self.session.flush()
        return entry

    # ── Delete Operations ───────────────────────────────────────────────────────────────────────────────────
    def remove_entry(self, entry_id: int, user_id: int) -> bool:
        """
        Remove a planner entry by ID if owned by the user.
        Does NOT delete the underlying meal.

        Args:
            entry_id: ID of the entry to remove
            user_id: ID of the user who owns the entry

        Returns:
            True if removed, False if not found/not owned
        """
        entry = self.get_by_id(entry_id, user_id)
        if entry:
            self.session.delete(entry)
            self.session.flush()
            return True
        return False

    # ── Utility Methods ─────────────────────────────────────────────────────────────────────────────────────
    def _get_next_position(self, user_id: int) -> int:
        """
        Get the next available position for a user.

        Args:
            user_id: ID of the user whose position to calculate

        Returns:
            Next position value
        """
        stmt = (
            select(func.max(PlannerEntry.position))
            .where(PlannerEntry.user_id == user_id)
        )
        max_pos = self.session.execute(stmt).scalar()
        return (max_pos or -1) + 1
