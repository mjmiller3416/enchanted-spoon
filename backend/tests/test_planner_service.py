"""Tests for the PlannerService (modular: Core + EntryManagement + StatusManagement + BatchOperations).

Covers:
- Read: get entry, get all entries (with filters), get summary
- Add: happy path, invalid meal, planner full
- Remove: success, not found
- Status: reorder, cycle shopping mode, mark completed, mark incomplete
- Batch: clear planner, clear completed
- Cooking Streak: pure algorithm tests for streak calculation
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.dtos.planner_dtos import (
    CookingStreakDTO,
    PlannerEntryResponseDTO,
    PlannerSummaryDTO,
)
from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.repositories.planner import MAX_PLANNER_ENTRIES
from app.services.planner import InvalidMealError, PlannerFullError, PlannerService
from app.services.planner.service import PlannerServiceCore


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

class TestPlannerServiceRead:
    """Tests for PlannerService read operations."""

    def test_get_entry(self, db_session, test_user, sample_planner_entry):
        """get_entry returns a DTO matching the planner entry."""
        service = PlannerService(db_session, test_user.id)

        result = service.get_entry(sample_planner_entry.id)

        assert result is not None
        assert isinstance(result, PlannerEntryResponseDTO)
        assert result.id == sample_planner_entry.id
        assert result.meal_id == sample_planner_entry.meal_id
        assert result.position == sample_planner_entry.position

    def test_get_entry_not_found(self, db_session, test_user):
        """get_entry returns None for a non-existent ID."""
        service = PlannerService(db_session, test_user.id)

        result = service.get_entry(9999)

        assert result is None

    def test_get_all_entries(self, db_session, test_user, sample_planner_entry):
        """get_all_entries returns all entries including the sample entry."""
        service = PlannerService(db_session, test_user.id)

        results = service.get_all_entries()

        assert len(results) >= 1
        entry_ids = [r.id for r in results]
        assert sample_planner_entry.id in entry_ids

    def test_get_all_entries_filter_completed(
        self, db_session, test_user, sample_planner_entry
    ):
        """get_all_entries(completed=False) returns the sample entry (incomplete by default)."""
        service = PlannerService(db_session, test_user.id)

        results = service.get_all_entries(completed=False)

        assert len(results) >= 1
        entry_ids = [r.id for r in results]
        assert sample_planner_entry.id in entry_ids
        assert all(not r.is_completed for r in results)

    def test_get_summary(self, db_session, test_user, sample_planner_entry):
        """get_summary returns correct counts for one incomplete entry."""
        service = PlannerService(db_session, test_user.id)

        result = service.get_summary()

        assert isinstance(result, PlannerSummaryDTO)
        assert result.total_entries == 1
        assert result.completed_entries == 0
        assert result.incomplete_entries == 1
        assert result.is_at_capacity is False
        assert result.max_capacity == MAX_PLANNER_ENTRIES


# ---------------------------------------------------------------------------
# Add Entry
# ---------------------------------------------------------------------------

@patch.object(PlannerServiceCore, "_sync_shopping_list")
class TestPlannerServiceAddEntry:
    """Tests for PlannerService.add_meal_to_planner."""

    def test_add_meal_to_planner(
        self, _mock_sync, db_session, test_user, sample_meal
    ):
        """Adding a valid meal creates a planner entry with the correct meal_id."""
        service = PlannerService(db_session, test_user.id)

        result = service.add_meal_to_planner(sample_meal.id)

        assert isinstance(result, PlannerEntryResponseDTO)
        assert result.meal_id == sample_meal.id
        assert result.is_completed is False

    def test_add_meal_invalid_id(self, _mock_sync, db_session, test_user):
        """Adding a non-existent meal raises InvalidMealError."""
        service = PlannerService(db_session, test_user.id)

        with pytest.raises(InvalidMealError, match="does not exist"):
            service.add_meal_to_planner(9999)

    def test_add_meal_planner_full(
        self, _mock_sync, db_session, test_user, sample_recipe
    ):
        """Adding a meal when the planner is at capacity raises PlannerFullError."""
        # Fill the planner to capacity with incomplete entries
        for i in range(MAX_PLANNER_ENTRIES):
            meal = Meal(
                meal_name=f"Filler Meal {i}",
                main_recipe_id=sample_recipe.id,
                user_id=test_user.id,
                is_saved=True,
            )
            db_session.add(meal)
            db_session.flush()

            entry = PlannerEntry(
                meal_id=meal.id,
                user_id=test_user.id,
                position=i,
            )
            db_session.add(entry)

        db_session.flush()

        # Create one more meal to attempt adding
        extra_meal = Meal(
            meal_name="One Too Many",
            main_recipe_id=sample_recipe.id,
            user_id=test_user.id,
            is_saved=True,
        )
        db_session.add(extra_meal)
        db_session.flush()

        service = PlannerService(db_session, test_user.id)

        with pytest.raises(PlannerFullError, match="maximum capacity"):
            service.add_meal_to_planner(extra_meal.id)

    def test_add_meal_completed_entries_free_capacity(
        self, _mock_sync, db_session, test_user, sample_recipe
    ):
        """Completed entries don't count toward the cap, so adding succeeds."""
        # Fill the planner to capacity, but mark one entry completed
        for i in range(MAX_PLANNER_ENTRIES):
            meal = Meal(
                meal_name=f"Filler Meal {i}",
                main_recipe_id=sample_recipe.id,
                user_id=test_user.id,
                is_saved=True,
            )
            db_session.add(meal)
            db_session.flush()

            entry = PlannerEntry(
                meal_id=meal.id,
                user_id=test_user.id,
                position=i,
                is_completed=(i == 0),
            )
            db_session.add(entry)

        db_session.flush()

        extra_meal = Meal(
            meal_name="Fits Thanks To Completed Slot",
            main_recipe_id=sample_recipe.id,
            user_id=test_user.id,
            is_saved=True,
        )
        db_session.add(extra_meal)
        db_session.flush()

        service = PlannerService(db_session, test_user.id)

        result = service.add_meal_to_planner(extra_meal.id)

        assert isinstance(result, PlannerEntryResponseDTO)
        assert result.meal_id == extra_meal.id


# ---------------------------------------------------------------------------
# Remove Entry
# ---------------------------------------------------------------------------

@patch.object(PlannerServiceCore, "_sync_shopping_list")
class TestPlannerServiceRemoveEntry:
    """Tests for PlannerService.remove_entry."""

    def test_remove_entry(
        self, _mock_sync, db_session, test_user, sample_planner_entry
    ):
        """Removing an existing entry returns True and the entry is gone afterward."""
        service = PlannerService(db_session, test_user.id)
        entry_id = sample_planner_entry.id

        result = service.remove_entry(entry_id)

        assert result is True
        assert service.get_entry(entry_id) is None

    def test_remove_entry_not_found(self, _mock_sync, db_session, test_user):
        """Removing a non-existent entry returns False."""
        service = PlannerService(db_session, test_user.id)

        result = service.remove_entry(9999)

        assert result is False


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@patch.object(PlannerServiceCore, "_sync_shopping_list")
class TestPlannerServiceStatus:
    """Tests for StatusManagementMixin: reorder, cycle shopping mode, completion."""

    def test_reorder_entries(
        self, _mock_sync, db_session, test_user, sample_recipe
    ):
        """Reordering entries assigns new positions in the specified order."""
        service = PlannerService(db_session, test_user.id)

        # Create two meals and add them to planner
        meal_a = Meal(
            meal_name="Meal A",
            main_recipe_id=sample_recipe.id,
            user_id=test_user.id,
            is_saved=True,
        )
        meal_b = Meal(
            meal_name="Meal B",
            main_recipe_id=sample_recipe.id,
            user_id=test_user.id,
            is_saved=True,
        )
        db_session.add_all([meal_a, meal_b])
        db_session.flush()

        entry_a = service.add_meal_to_planner(meal_a.id)
        entry_b = service.add_meal_to_planner(meal_b.id)

        # Reorder: B first, then A
        result = service.reorder_entries([entry_b.id, entry_a.id])
        assert result is True

        # Verify new positions
        refreshed_b = service.get_entry(entry_b.id)
        refreshed_a = service.get_entry(entry_a.id)
        assert refreshed_b.position == 0
        assert refreshed_a.position == 1

    def test_cycle_shopping_mode(
        self, _mock_sync, db_session, test_user, sample_planner_entry
    ):
        """Cycling shopping mode follows the sequence: all -> produce_only -> none -> all."""
        service = PlannerService(db_session, test_user.id)
        entry_id = sample_planner_entry.id

        # Default is "all"
        initial = service.get_entry(entry_id)
        assert initial.shopping_mode == "all"

        # Cycle 1: all -> produce_only
        result1 = service.cycle_shopping_mode(entry_id)
        assert result1.shopping_mode == "produce_only"

        # Cycle 2: produce_only -> none
        result2 = service.cycle_shopping_mode(entry_id)
        assert result2.shopping_mode == "none"

        # Cycle 3: none -> all
        result3 = service.cycle_shopping_mode(entry_id)
        assert result3.shopping_mode == "all"

    def test_mark_completed(
        self, _mock_sync, db_session, test_user, sample_planner_entry
    ):
        """Marking an entry as completed sets is_completed and completed_at."""
        service = PlannerService(db_session, test_user.id)
        entry_id = sample_planner_entry.id

        result = service.mark_completed(entry_id)

        assert result is not None
        assert result.is_completed is True
        assert result.completed_at is not None

    def test_mark_incomplete(
        self, _mock_sync, db_session, test_user, sample_planner_entry
    ):
        """Marking a completed entry as incomplete clears is_completed."""
        service = PlannerService(db_session, test_user.id)
        entry_id = sample_planner_entry.id

        # First complete it
        service.mark_completed(entry_id)

        # Then mark incomplete
        result = service.mark_incomplete(entry_id)

        assert result is not None
        assert result.is_completed is False


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

@patch.object(PlannerServiceCore, "_sync_shopping_list")
class TestPlannerServiceBatch:
    """Tests for BatchOperationsMixin: clear_planner, clear_completed."""

    def test_clear_planner(
        self, _mock_sync, db_session, test_user, sample_planner_entry
    ):
        """Clearing the planner removes all entries and returns the count."""
        service = PlannerService(db_session, test_user.id)

        count = service.clear_planner()

        assert count == 1
        assert service.get_all_entries() == []

    def test_clear_completed(
        self, _mock_sync, db_session, test_user, sample_planner_entry
    ):
        """Clearing completed entries removes only completed ones."""
        service = PlannerService(db_session, test_user.id)
        entry_id = sample_planner_entry.id

        # Mark the entry as completed first
        service.mark_completed(entry_id)

        count = service.clear_completed()

        assert count == 1
        # No completed entries remain
        assert service.get_all_entries(completed=True) == []


# ---------------------------------------------------------------------------
# Cooking Streak (pure algorithm tests — no DB needed)
# ---------------------------------------------------------------------------

class TestCookingStreak:
    """Tests for the private streak calculation methods on PlannerServiceCore.

    These are pure functions operating on date sets, so we bypass __init__
    and test the algorithm directly.
    """

    @pytest.fixture(autouse=True)
    def setup_core(self):
        """Create a bare PlannerServiceCore without full initialization."""
        self.core = PlannerServiceCore.__new__(PlannerServiceCore)
        self.today = date(2026, 6, 18)  # Thursday

    def test_current_streak_today_cooked(self):
        """A 3-day streak ending today returns 3."""
        cooked = {
            self.today,
            self.today - timedelta(days=1),
            self.today - timedelta(days=2),
        }

        result = self.core._calculate_current_streak(cooked, self.today)

        assert result == 3

    def test_current_streak_gap(self):
        """A gap at yesterday breaks the streak even if day-before is cooked."""
        cooked = {
            self.today,
            self.today - timedelta(days=2),  # yesterday missing
        }

        result = self.core._calculate_current_streak(cooked, self.today)

        assert result == 1

    def test_current_streak_empty(self):
        """An empty set of cooked dates returns a streak of 0."""
        result = self.core._calculate_current_streak(set(), self.today)

        assert result == 0

    def test_longest_streak(self):
        """The longest streak is correctly identified across multiple runs."""
        # 5-day streak: June 1-5
        five_day = {date(2026, 6, d) for d in range(1, 6)}
        # 3-day streak: June 10-12
        three_day = {date(2026, 6, d) for d in range(10, 13)}

        cooked = five_day | three_day

        result = self.core._calculate_longest_streak(cooked)

        assert result == 5

    def test_longest_streak_empty(self):
        """An empty set returns 0 for longest streak."""
        result = self.core._calculate_longest_streak(set())

        assert result == 0

    def test_week_activity(self):
        """Week activity returns correct booleans for Monday-Sunday."""
        # 2026-06-18 is a Thursday (weekday index 3)
        # Monday of that week is 2026-06-15
        cooked = {
            date(2026, 6, 15),  # Monday
            date(2026, 6, 17),  # Wednesday
            date(2026, 6, 18),  # Thursday (today)
        }

        result = self.core._get_week_activity(cooked, self.today)

        assert len(result) == 7
        #       Mon    Tue    Wed    Thu    Fri    Sat    Sun
        assert result == [True, False, True, True, False, False, False]

    def test_week_activity_empty(self):
        """No cooked dates produces an all-False week."""
        result = self.core._get_week_activity(set(), self.today)

        assert result == [False] * 7
