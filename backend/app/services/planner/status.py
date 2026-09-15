"""app/services/planner/status.py

Status management mixin for planner service.
Handles reordering, shopping mode, and completion status.
"""

# -- Imports -------------------------------------------------------------------------------------
import logging
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from ...dtos.planner_dtos import PlannerEntryResponseDTO, PlannerShoppingModeDTO
from .entry import EntryNotFoundError


class ShoppingModeSaveError(Exception):
    """Raised when a shopping mode cannot be saved."""


# -- Status Management Mixin ---------------------------------------------------------------------
class StatusManagementMixin:
    """Mixin providing status management and reordering methods."""

    # -- Update Operations -----------------------------------------------------------------------
    def reorder_entries(self, entry_ids: List[int]) -> bool:
        """
        Reorder planner entries for the current user.

        Args:
            entry_ids: List of entry IDs in desired order

        Returns:
            True if successful
        """
        try:
            result = self.repo.reorder_entries(entry_ids, self.user_id)
            self.session.commit()
            return result
        except SQLAlchemyError:
            self.session.rollback()
            return False

    def set_shopping_mode(self, entry_id: int, data: PlannerShoppingModeDTO) -> PlannerEntryResponseDTO:
        """Set the requested state instead of cycling from an uncertain state."""
        try:
            entry = self.repo.get_by_id(entry_id, self.user_id)
            if not entry:
                raise EntryNotFoundError("Planner entry not found")
            entry.shopping_mode = data.shopping_mode
            self.repo.update(entry)
            self.session.commit()
            self._sync_shopping_list()
            return self._entry_to_response_dto(entry)
        except SQLAlchemyError as error:
            self.session.rollback()
            raise ShoppingModeSaveError("Couldn't update the shopping mode") from error

    def cycle_shopping_mode(self, entry_id: int) -> Optional[PlannerEntryResponseDTO]:
        """
        Cycle the shopping mode of a planner entry for the current user: all -> produce_only -> none -> all.

        Args:
            entry_id: ID of the entry

        Returns:
            Updated entry as DTO or None if not found/not owned
        """
        try:
            entry = self.repo.cycle_shopping_mode(entry_id, self.user_id)
            if not entry:
                return None

            self.session.commit()

            # Sync shopping list after mode change
            self._sync_shopping_list()

            entry = self.repo.get_by_id(entry.id, self.user_id)
            return self._entry_to_response_dto(entry)
        except SQLAlchemyError:
            self.session.rollback()
            return None

    def mark_completed(self, entry_id: int) -> Optional[PlannerEntryResponseDTO]:
        """
        Mark a planner entry as completed for the current user.

        Args:
            entry_id: ID of the entry

        Returns:
            Updated entry as DTO or None if not found/not owned
        """
        try:
            logging.info(f"mark_completed: entry_id={entry_id}, user_id={self.user_id}")

            entry = self.repo.mark_completed(entry_id, self.user_id)

            logging.info(f"mark_completed: repo returned entry={entry}")

            if not entry:
                return None

            # Record cooking history for the main recipe
            if entry.meal and entry.meal.main_recipe_id:
                self.recipe_repo.record_cooked(
                    entry.meal.main_recipe_id, self.user_id
                )

            self.session.commit()

            # Sync shopping list (completed entries are excluded from shopping)
            # Non-blocking: don't let sync failures block meal completion
            try:
                self._sync_shopping_list()
            except Exception as e:
                logging.warning(
                    f"Shopping list sync failed after meal completion: {e}"
                )

            entry = self.repo.get_by_id(entry.id, self.user_id)
            return self._entry_to_response_dto(entry)
        except SQLAlchemyError as e:
            logging.error(f"mark_completed SQLAlchemyError: {e}")
            self.session.rollback()
            return None

    def mark_incomplete(self, entry_id: int) -> Optional[PlannerEntryResponseDTO]:
        """
        Mark a planner entry as incomplete for the current user.

        Args:
            entry_id: ID of the entry

        Returns:
            Updated entry as DTO or None if not found/not owned
        """
        try:
            entry = self.repo.mark_incomplete(entry_id, self.user_id)
            if not entry:
                return None

            self.session.commit()

            # Sync shopping list (now this entry contributes to shopping again)
            self._sync_shopping_list()

            entry = self.repo.get_by_id(entry.id, self.user_id)
            return self._entry_to_response_dto(entry)
        except SQLAlchemyError:
            self.session.rollback()
            return None
