"""app/services/planner/entry.py

Entry CRUD mixin for planner service.
Handles entry creation, removal, and transient meal cleanup.
"""

# -- Imports -------------------------------------------------------------------------------------
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from ...dtos.planner_dtos import PlannerEntryResponseDTO
from ...repositories.planner import MAX_PLANNER_ENTRIES


# -- Domain Exceptions ---------------------------------------------------------------------------
class PlannerFullError(Exception):
    """Raised when the planner is at maximum capacity."""

    pass


class InvalidMealError(Exception):
    """Raised when a meal ID is invalid."""

    pass


class EntryNotFoundError(Exception):
    """Raised when a planner entry is not found."""

    pass


# -- Entry Management Mixin ----------------------------------------------------------------------
class EntryManagementMixin:
    """Mixin providing entry creation and removal methods."""

    # -- Add to Planner --------------------------------------------------------------------------
    def add_meal_to_planner(
        self, meal_id: int, position: Optional[int] = None
    ) -> PlannerEntryResponseDTO:
        """
        Add a meal to the planner for the current user.

        Args:
            meal_id: ID of the meal to add
            position: Optional position (defaults to end)

        Returns:
            Created planner entry as DTO

        Raises:
            PlannerFullError: If planner is at capacity (MAX_PLANNER_ENTRIES
                incomplete entries — completed meals don't count)
            InvalidMealError: If meal ID doesn't exist or isn't owned by user
        """
        try:
            # Check capacity
            if self.repo.is_at_capacity(self.user_id):
                raise PlannerFullError(
                    f"Planner is at maximum capacity ({MAX_PLANNER_ENTRIES} entries)"
                )

            # Validate meal exists and belongs to user
            valid_ids = self.meal_repo.validate_meal_ids([meal_id], self.user_id)
            if meal_id not in valid_ids:
                raise InvalidMealError(f"Meal ID {meal_id} does not exist")

            # Add entry
            entry = self.repo.add_entry(meal_id, self.user_id, position)
            self.session.commit()

            # Sync shopping list after adding meal
            self._sync_shopping_list()

            # Refresh to get relationships
            entry = self.repo.get_by_id(entry.id, self.user_id)
            return self._entry_to_response_dto(entry)

        except (PlannerFullError, InvalidMealError):
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to add meal to planner: {e}") from e

    def add_meals_to_planner(
        self, meal_ids: List[int]
    ) -> List[PlannerEntryResponseDTO]:
        """
        Add multiple meals to the planner for the current user.

        Args:
            meal_ids: List of meal IDs to add

        Returns:
            List of created planner entries as DTOs

        Raises:
            PlannerFullError: If adding would exceed capacity
            InvalidMealError: If any meal ID doesn't exist or isn't owned by user
        """
        try:
            current_count = self.repo.count_incomplete(self.user_id)
            if current_count + len(meal_ids) > MAX_PLANNER_ENTRIES:
                raise PlannerFullError(
                    f"Cannot add {len(meal_ids)} meals: would exceed "
                    f"maximum capacity ({MAX_PLANNER_ENTRIES})"
                )

            # Validate all meal IDs belong to user
            valid_ids = self.meal_repo.validate_meal_ids(meal_ids, self.user_id)
            invalid_ids = [mid for mid in meal_ids if mid not in valid_ids]
            if invalid_ids:
                raise InvalidMealError(f"Meal IDs {invalid_ids} do not exist")

            # Add entries
            entries = []
            for meal_id in meal_ids:
                entry = self.repo.add_entry(meal_id, self.user_id)
                entries.append(entry)

            self.session.commit()

            # Sync shopping list after adding meals
            self._sync_shopping_list()

            # Refresh and convert to DTOs
            result = []
            for entry in entries:
                entry = self.repo.get_by_id(entry.id, self.user_id)
                result.append(self._entry_to_response_dto(entry))

            return result

        except (PlannerFullError, InvalidMealError):
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to add meals to planner: {e}") from e

    # -- Transient Meal Cleanup ------------------------------------------------------------------
    def _cleanup_transient_meal(self, meal_id: int) -> None:
        """
        Delete a meal if it's transient and has no remaining planner references.

        Called after removing or clearing planner entries to clean up
        transient meals that are no longer in use.

        IMPORTANT: Uses count_all_entries_for_meal to preserve cooking history.
        Cleared entries with cooking streak data must prevent meal deletion.

        Args:
            meal_id: ID of the meal to potentially clean up
        """
        meal = self.meal_repo.get_by_id(meal_id, self.user_id)
        if meal and not meal.is_saved:
            # Check ALL entries (active + cleared) to preserve cooking history
            remaining = self.repo.count_all_entries_for_meal(meal_id, self.user_id)
            if remaining == 0:
                self.meal_repo.delete(meal_id, self.user_id)

    # -- Remove Operations -----------------------------------------------------------------------
    def remove_entry(self, entry_id: int) -> bool:
        """
        Remove a planner entry for the current user.
        Transient meals are deleted if this was their last reference.

        Args:
            entry_id: ID of the entry

        Returns:
            True if removed, False if not found/not owned
        """
        try:
            # Get entry first to capture meal_id before deletion
            entry = self.repo.get_by_id(entry_id, self.user_id)
            if not entry:
                return False

            meal_id = entry.meal_id
            result = self.repo.remove_entry(entry_id, self.user_id)

            if result:
                # Clean up transient meal if no longer referenced
                self._cleanup_transient_meal(meal_id)

            self.session.commit()

            # Sync shopping list after removing entry
            if result:
                self._sync_shopping_list()

            return result
        except SQLAlchemyError:
            self.session.rollback()
            return False

    def remove_entries_by_meal(self, meal_id: int) -> int:
        """
        Remove all planner entries for a specific meal for the current user.

        Args:
            meal_id: ID of the meal

        Returns:
            Number of entries removed
        """
        try:
            count = self.repo.remove_entries_by_meal_id(meal_id, self.user_id)
            self.session.commit()

            # Sync shopping list after removing entries
            if count > 0:
                self._sync_shopping_list()

            return count
        except SQLAlchemyError:
            self.session.rollback()
            return 0
