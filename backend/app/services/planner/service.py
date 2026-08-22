"""app/services/planner/service.py

Core planner service with initialization, read operations, and helper methods.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Set
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...dtos.planner_dtos import (
    CookingStreakDTO,
    PlannerEntryResponseDTO,
    PlannerSummaryDTO,
    RecipeCardDTO,
)
from ...models.planner_entry import PlannerEntry
from ...repositories.meal_repo import MealRepo
from ...repositories.planner import MAX_PLANNER_ENTRIES, PlannerRepo
from ...repositories.recipe_repo import RecipeRepo


# -- Core Service --------------------------------------------------------------------------------
class PlannerServiceCore:
    """Core planner service with initialization and read operations."""

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the PlannerService with a database session and user ID.

        Args:
            session: SQLAlchemy database session (required).
            user_id: ID of the authenticated user (required for multi-tenant isolation).
        """
        self.session = session
        self.user_id = user_id
        self.repo = PlannerRepo(self.session)
        self.meal_repo = MealRepo(self.session)
        self.recipe_repo = RecipeRepo(self.session, user_id=user_id)

    # -- Shopping List Sync Helper ---------------------------------------------------------------
    def _sync_shopping_list(self) -> None:
        """
        Sync the shopping list after planner mutations.
        This is called automatically after any operation that affects what should
        be in the shopping list.
        """
        from ..shopping import ShoppingService

        shopping_service = ShoppingService(self.session, self.user_id)
        shopping_service.sync_shopping_list()

    # -- Read Operations -------------------------------------------------------------------------
    def get_entry(self, entry_id: int) -> Optional[PlannerEntryResponseDTO]:
        """
        Get a planner entry by ID for the current user.

        Args:
            entry_id: ID of the entry

        Returns:
            Entry as DTO or None if not found/not owned
        """
        try:
            entry = self.repo.get_by_id(entry_id, self.user_id)
            return self._entry_to_response_dto(entry) if entry else None
        except SQLAlchemyError:
            return None

    def get_all_entries(
        self,
        meal_id: Optional[int] = None,
        completed: Optional[bool] = None,
    ) -> List[PlannerEntryResponseDTO]:
        """
        Get planner entries with optional filtering for the current user.

        Args:
            meal_id: Filter by specific meal ID
            completed: Filter by completion status (True/False/None for all)

        Returns:
            List of entries as DTOs matching the filters
        """
        try:
            # Apply filters based on parameters
            if meal_id is not None:
                entries = self.repo.get_by_meal_id(meal_id, self.user_id)
                # Apply completion filter if also specified
                if completed is not None:
                    entries = [e for e in entries if e.is_completed == completed]
            elif completed is True:
                entries = self.repo.get_completed_entries(self.user_id)
            elif completed is False:
                entries = self.repo.get_incomplete_entries(self.user_id)
            else:
                entries = self.repo.get_all(self.user_id)

            return [self._entry_to_response_dto(e) for e in entries]
        except SQLAlchemyError:
            return []

    def get_meal_ids(self) -> List[int]:
        """
        Get all meal IDs in the planner for the current user.

        Returns:
            List of meal IDs in position order
        """
        try:
            return self.repo.get_meal_ids(self.user_id)
        except SQLAlchemyError:
            return []

    def get_summary(self) -> PlannerSummaryDTO:
        """
        Get a summary of the current planner state for the current user.

        Returns:
            PlannerSummaryDTO with counts and status
        """
        try:
            entries = self.repo.get_all(self.user_id)
            total_entries = len(entries)
            completed = sum(1 for e in entries if e.is_completed)

            # Count total recipes across all meals
            total_recipes = 0
            meal_names = []
            for entry in entries:
                if entry.meal:
                    meal_names.append(entry.meal.meal_name)
                    total_recipes += 1 + len(entry.meal.side_recipe_ids)

            return PlannerSummaryDTO(
                total_entries=total_entries,
                completed_entries=completed,
                incomplete_entries=total_entries - completed,
                total_recipes=total_recipes,
                meal_names=meal_names,
                is_at_capacity=((total_entries - completed) >= MAX_PLANNER_ENTRIES),
                max_capacity=MAX_PLANNER_ENTRIES,
            )
        except SQLAlchemyError as e:
            return PlannerSummaryDTO(
                total_entries=0,
                completed_entries=0,
                incomplete_entries=0,
                total_recipes=0,
                meal_names=[],
                is_at_capacity=False,
                max_capacity=MAX_PLANNER_ENTRIES,
                error=str(e),
            )

    def get_cooking_streak(
        self, user_timezone: Optional[str] = None
    ) -> CookingStreakDTO:
        """
        Get cooking streak information based on completed meals for the current user.

        Calculates:
        - Current consecutive day streak (breaks if a day is missed)
        - Longest streak ever achieved
        - Current week's activity (Monday-Sunday)

        Args:
            user_timezone: IANA timezone string (e.g., 'America/New_York').
                          If not provided, uses server's local timezone.

        Returns:
            CookingStreakDTO with streak and activity data
        """
        try:
            # Get all entries with completion history (includes cleared entries)
            entries = self.repo.get_cooking_history_entries(self.user_id)

            # Determine the timezone to use for date calculations
            try:
                tz = ZoneInfo(user_timezone) if user_timezone else None
            except (KeyError, ValueError):
                tz = None  # Fall back to server timezone if invalid

            # Extract unique dates when meals were cooked (convert UTC to user's timezone)
            cooked_dates: Set[date] = set()
            for entry in entries:
                if entry.completed_at:
                    # completed_at is stored as UTC - convert to user's timezone for correct date
                    utc_time = entry.completed_at.replace(tzinfo=timezone.utc)
                    local_time = utc_time.astimezone(tz)
                    cooked_dates.add(local_time.date())

            # Get "today" in user's timezone
            today = datetime.now(tz).date() if tz else date.today()

            # Calculate current streak (consecutive days ending today or yesterday)
            current_streak = self._calculate_current_streak(cooked_dates, today)

            # Calculate longest streak ever
            longest_streak = self._calculate_longest_streak(cooked_dates)

            # Calculate current week activity (Monday = 0, Sunday = 6)
            week_activity = self._get_week_activity(cooked_dates, today)

            # Get last cooked date
            last_cooked = max(cooked_dates) if cooked_dates else None

            return CookingStreakDTO(
                current_streak=current_streak,
                longest_streak=max(longest_streak, current_streak),
                week_activity=week_activity,
                last_cooked_date=last_cooked.isoformat() if last_cooked else None,
                today_index=today.weekday(),  # 0=Monday, 6=Sunday
            )

        except SQLAlchemyError:
            return CookingStreakDTO(
                current_streak=0,
                longest_streak=0,
                week_activity=[False] * 7,
                last_cooked_date=None,
                today_index=date.today().weekday(),
            )

    def _calculate_current_streak(self, cooked_dates: Set[date], today: date) -> int:
        """Calculate consecutive days ending today or yesterday."""
        if not cooked_dates:
            return 0

        # Start from today and count backwards
        streak = 0
        check_date = today

        # If today isn't cooked yet, start from yesterday
        if today not in cooked_dates:
            check_date = today - timedelta(days=1)
            # If yesterday also wasn't cooked, streak is 0
            if check_date not in cooked_dates:
                return 0

        # Count consecutive days backwards
        while check_date in cooked_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    def _calculate_longest_streak(self, cooked_dates: Set[date]) -> int:
        """Calculate the longest consecutive day streak ever."""
        if not cooked_dates:
            return 0

        sorted_dates = sorted(cooked_dates)
        longest = 1
        current = 1

        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
                current += 1
                longest = max(longest, current)
            else:
                current = 1

        return longest

    def _get_week_activity(self, cooked_dates: Set[date], today: date) -> List[bool]:
        """Get activity for current calendar week (Monday-Sunday)."""
        # Find Monday of current week
        days_since_monday = today.weekday()  # Monday = 0, Sunday = 6
        monday = today - timedelta(days=days_since_monday)

        # Check each day of the week
        week_activity = []
        for i in range(7):
            day = monday + timedelta(days=i)
            week_activity.append(day in cooked_dates)

        return week_activity

    # -- Helper Methods --------------------------------------------------------------------------
    def _entry_to_response_dto(self, entry: PlannerEntry) -> PlannerEntryResponseDTO:
        """
        Convert a PlannerEntry model to a response DTO.

        Args:
            entry: PlannerEntry model

        Returns:
            PlannerEntryResponseDTO
        """
        meal = entry.meal
        return PlannerEntryResponseDTO(
            id=entry.id,
            meal_id=entry.meal_id,
            position=entry.position,
            is_completed=entry.is_completed,
            completed_at=(
                entry.completed_at.isoformat() if entry.completed_at else None
            ),
            scheduled_date=(
                entry.scheduled_date.isoformat() if entry.scheduled_date else None
            ),
            shopping_mode=entry.shopping_mode,
            meal_name=meal.meal_name if meal else None,
            meal_is_saved=meal.is_saved if meal else None,
            main_recipe_id=meal.main_recipe_id if meal else None,
            side_recipe_ids=meal.side_recipe_ids if meal else [],
            main_recipe=RecipeCardDTO.from_recipe(meal.main_recipe) if meal else None,
        )
