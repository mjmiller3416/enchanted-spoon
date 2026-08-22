"""app/repositories/planner

Planner repository package with modular structure.
Provides entry operations, queries, and statistics management.
"""

from sqlalchemy.orm import Session

from .entry_repo import PlannerEntryRepo
from .query_repo import PlannerQueryRepo
from .stats_repo import MAX_PLANNER_ENTRIES, PlannerStatsRepo


class PlannerRepo:
    """Unified planner repository that delegates to specialized sub-repositories.

    Provides backwards compatibility while maintaining modular structure.
    """

    def __init__(self, session: Session):
        """Initialize the unified Planner Repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

        # Initialize sub-repositories
        self.entry_repo = PlannerEntryRepo(session)
        self.query_repo = PlannerQueryRepo(session)
        self.stats_repo = PlannerStatsRepo(session)

    # ── Entry Operations (delegate to entry_repo) ──────────────────────────────────────────────────────────
    def add_entry(self, meal_id, user_id, position=None):
        """Add a meal to the planner."""
        return self.entry_repo.add_entry(meal_id, user_id, position)

    def get_by_id(self, entry_id, user_id=None):
        """Get a planner entry by ID."""
        return self.entry_repo.get_by_id(entry_id, user_id)

    def update(self, entry):
        """Update a planner entry."""
        return self.entry_repo.update(entry)

    def update_position(self, entry_id, new_position, user_id):
        """Update the position of a planner entry."""
        return self.entry_repo.update_position(entry_id, new_position, user_id)

    def mark_completed(self, entry_id, user_id):
        """Mark a planner entry as completed."""
        return self.entry_repo.mark_completed(entry_id, user_id)

    def mark_incomplete(self, entry_id, user_id):
        """Mark a planner entry as incomplete."""
        return self.entry_repo.mark_incomplete(entry_id, user_id)

    def cycle_shopping_mode(self, entry_id, user_id):
        """Cycle the shopping mode of a planner entry."""
        return self.entry_repo.cycle_shopping_mode(entry_id, user_id)

    def remove_entry(self, entry_id, user_id):
        """Remove a planner entry by ID."""
        return self.entry_repo.remove_entry(entry_id, user_id)

    # ── Query Operations (delegate to query_repo) ──────────────────────────────────────────────────────────
    def get_all(self, user_id):
        """Get all active planner entries."""
        return self.query_repo.get_all(user_id)

    def get_by_meal_id(self, meal_id, user_id):
        """Get all planner entries for a specific meal."""
        return self.query_repo.get_by_meal_id(meal_id, user_id)

    def get_meal_ids(self, user_id):
        """Get all meal IDs currently in the planner."""
        return self.query_repo.get_meal_ids(user_id)

    def get_completed_entries(self, user_id):
        """Get all completed planner entries."""
        return self.query_repo.get_completed_entries(user_id)

    def get_cooking_history_entries(self, user_id):
        """Get all entries with completion history."""
        return self.query_repo.get_cooking_history_entries(user_id)

    def get_incomplete_entries(self, user_id):
        """Get all incomplete planner entries."""
        return self.query_repo.get_incomplete_entries(user_id)

    def get_shopping_entries(self, user_id):
        """Get incomplete entries with shopping mode enabled."""
        return self.query_repo.get_shopping_entries(user_id)

    # ── Stats Operations (delegate to stats_repo) ──────────────────────────────────────────────────────────
    def count(self, user_id):
        """Count total number of active planner entries."""
        return self.stats_repo.count(user_id)

    def count_incomplete(self, user_id):
        """Count incomplete planner entries (capacity check)."""
        return self.stats_repo.count_incomplete(user_id)

    def count_completed(self, user_id):
        """Count completed planner entries."""
        return self.stats_repo.count_completed(user_id)

    def count_active_entries_for_meal(self, meal_id, user_id):
        """Count active entries for a specific meal."""
        return self.stats_repo.count_active_entries_for_meal(meal_id, user_id)

    def count_all_entries_for_meal(self, meal_id, user_id):
        """Count all entries (including cleared) for a specific meal."""
        return self.stats_repo.count_all_entries_for_meal(meal_id, user_id)

    def get_completion_stats_for_meal(self, meal_id, user_id):
        """Get completion statistics for a specific meal."""
        return self.stats_repo.get_completion_stats_for_meal(meal_id, user_id)

    def is_at_capacity(self, user_id):
        """Check if the planner is at maximum capacity."""
        return self.stats_repo.is_at_capacity(user_id)

    def reorder_entries(self, entry_ids, user_id):
        """Reorder entries based on the provided ID order."""
        return self.stats_repo.reorder_entries(entry_ids, user_id)

    def remove_entries_by_meal_id(self, meal_id, user_id):
        """Remove all planner entries for a specific meal."""
        return self.stats_repo.remove_entries_by_meal_id(meal_id, user_id)

    def clear_all(self, user_id):
        """Clear all planner entries."""
        return self.stats_repo.clear_all(user_id)

    def clear_completed(self, user_id):
        """Soft-delete all completed planner entries."""
        return self.stats_repo.clear_completed(user_id)


__all__ = [
    # Unified repository (backwards compatible)
    "PlannerRepo",
    # Individual repositories (for direct use if needed)
    "PlannerEntryRepo",
    "PlannerQueryRepo",
    "PlannerStatsRepo",
    # Constants
    "MAX_PLANNER_ENTRIES",
]
