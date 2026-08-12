"""app/core/repositories/meal_repo.py

Repository for managing meal CRUD operations.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..models.meal import Meal
from ..models.recipe import Recipe

# Safety backstop for list queries that omit an explicit limit.
MAX_LIST_ROWS = 1000


# -- Meal Repository -----------------------------------------------------------------------------
class MealRepo:
    """Repository for meal operations."""

    MAX_SIDE_RECIPES = 3

    def __init__(self, session: Session):
        """Initialize the Meal Repository with a database session."""
        self.session = session

    # -- Create Operations -----------------------------------------------------------------------
    def create_meal(self, meal: Meal, user_id: int) -> Meal:
        """
        Create and persist a new Meal to the database.

        Args:
            meal: Unsaved Meal instance (id should be None)
            user_id: ID of the user who owns this meal

        Returns:
            Saved Meal with assigned ID
        """
        if meal.id is not None:
            raise ValueError("Cannot create a meal that already has an ID.")

        meal.user_id = user_id
        self.session.add(meal)
        self.session.flush()
        self.session.refresh(meal)
        return meal

    # -- Read Operations -------------------------------------------------------------------------
    def get_by_id(self, meal_id: int, user_id: Optional[int] = None) -> Optional[Meal]:
        """
        Get a meal by ID with eager-loaded main recipe.

        Args:
            meal_id: ID of the meal to load
            user_id: If provided, only return the meal if it belongs to this user.
                Returns None if the meal exists but belongs to a different user (no existence leak).

        Returns:
            Meal if found and owned by user, None otherwise
        """
        stmt = (
            select(Meal)
            .where(Meal.id == meal_id)
            .options(joinedload(Meal.main_recipe))
        )
        if user_id is not None:
            stmt = stmt.where(Meal.user_id == user_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_all(self, user_id: int) -> List[Meal]:
        """
        Get all meals with eager-loaded main recipes for a specific user.

        Args:
            user_id: ID of the user whose meals to retrieve

        Returns:
            List of all meals belonging to the user
        """
        stmt = (
            select(Meal)
            .where(Meal.user_id == user_id)
            .options(joinedload(Meal.main_recipe))
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_by_name_pattern(self, name_pattern: str, user_id: int) -> List[Meal]:
        """
        Get meals by name pattern (case-insensitive) for a specific user.

        Args:
            name_pattern: Pattern to search for in meal names
            user_id: ID of the user whose meals to search

        Returns:
            List of matching meals belonging to the user
        """
        stmt = (
            select(Meal)
            .where(Meal.user_id == user_id)
            .where(Meal.meal_name.ilike(f"%{name_pattern}%"))
            .options(joinedload(Meal.main_recipe))
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_by_tags(self, tags: List[str], user_id: int, match_all: bool = True) -> List[Meal]:
        """
        Get meals that have the specified tags (case-insensitive) for a specific user.

        Args:
            tags: List of tags to filter by
            user_id: ID of the user whose meals to search
            match_all: If True, meals must have ALL tags. If False, any tag matches.

        Returns:
            List of matching meals belonging to the user
        """
        # For SQLite, we need to check the JSON array
        # Using LIKE with LOWER for case-insensitive matching
        meals = self.get_all(user_id)
        matching_meals = []

        tags_lower = [t.lower() for t in tags]

        for meal in meals:
            meal_tags_lower = [t.lower() for t in meal.tags]
            if match_all:
                if all(tag in meal_tags_lower for tag in tags_lower):
                    matching_meals.append(meal)
            else:
                if any(tag in meal_tags_lower for tag in tags_lower):
                    matching_meals.append(meal)

        return matching_meals

    def filter_meals(
        self,
        user_id: int,
        name_pattern: Optional[str] = None,
        tags: Optional[List[str]] = None,
        saved_only: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Meal]:
        """
        Filter meals with multiple criteria (stackable filters) for a specific user.

        Args:
            user_id: ID of the user whose meals to filter
            name_pattern: Optional name search pattern
            tags: Optional list of tags to filter by (AND logic)
            saved_only: If True, only saved meals; if False, only transient; if None, all
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching meals belonging to the user
        """
        stmt = select(Meal).options(joinedload(Meal.main_recipe))

        # Always filter by user - users only see their own meals
        stmt = stmt.where(Meal.user_id == user_id)

        if name_pattern:
            stmt = stmt.where(Meal.meal_name.ilike(f"%{name_pattern}%"))

        if saved_only is not None:
            stmt = stmt.where(Meal.is_saved == saved_only)

        # Order by creation date (newest first)
        stmt = stmt.order_by(Meal.created_at.desc())

        if offset:
            stmt = stmt.offset(offset)

        # Cap results when no explicit limit is given (see MAX_LIST_ROWS).
        stmt = stmt.limit(limit or MAX_LIST_ROWS)

        result = self.session.execute(stmt)
        meals = result.scalars().unique().all()

        # Filter by tags in Python (SQLite JSON support is limited)
        if tags:
            tags_lower = [t.lower() for t in tags]
            meals = [
                m for m in meals
                if all(tag in [t.lower() for t in m.tags] for tag in tags_lower)
            ]

        return meals

    # -- Update Operations -----------------------------------------------------------------------
    def update(self, meal: Meal) -> Meal:
        """
        Update an existing Meal in the database.

        Args:
            meal: Meal instance with valid ID

        Returns:
            Updated meal
        """
        if meal.id is None:
            raise ValueError("Cannot update a meal without an ID.")

        merged_meal = self.session.merge(meal)
        self.session.flush()
        return merged_meal

    # -- Delete Operations -----------------------------------------------------------------------
    def delete(self, meal_id: int, user_id: int) -> bool:
        """
        Delete a meal by ID if it belongs to the user.

        Args:
            meal_id: ID of the meal to delete
            user_id: ID of the user who owns the meal

        Returns:
            True if deleted, False if not found or not owned
        """
        meal = self.get_by_id(meal_id, user_id)
        if meal:
            self.session.delete(meal)
            self.session.flush()
            return True
        return False

    # -- Recipe Relationship Operations ----------------------------------------------------------
    def get_meals_by_main_recipe(self, recipe_id: int, user_id: int) -> List[Meal]:
        """
        Get all meals that use a recipe as their main recipe for a specific user.

        Args:
            recipe_id: ID of the recipe
            user_id: ID of the user whose meals to search

        Returns:
            List of meals with this recipe as main belonging to the user
        """
        stmt = (
            select(Meal)
            .where(Meal.user_id == user_id)
            .where(Meal.main_recipe_id == recipe_id)
            .options(joinedload(Meal.main_recipe))
        )
        result = self.session.execute(stmt)
        return result.scalars().unique().all()

    def get_meals_with_side_recipe(self, recipe_id: int, user_id: int) -> List[Meal]:
        """
        Get all meals that have a recipe in their side recipes for a specific user.

        Args:
            recipe_id: ID of the recipe
            user_id: ID of the user whose meals to search

        Returns:
            List of meals containing this recipe as a side belonging to the user
        """
        # Need to search JSON array - for SQLite we search the text
        meals = self.get_all(user_id)
        return [m for m in meals if recipe_id in m.side_recipe_ids]

    def get_meals_containing_recipe(self, recipe_id: int, user_id: int) -> List[Meal]:
        """
        Get all meals that contain a recipe (main or side) for a specific user.

        Args:
            recipe_id: ID of the recipe
            user_id: ID of the user whose meals to search

        Returns:
            List of meals containing this recipe belonging to the user
        """
        meals = self.get_all(user_id)
        return [m for m in meals if m.has_recipe(recipe_id)]

    def remove_side_recipe_from_all_meals(self, recipe_id: int, user_id: int) -> int:
        """
        Remove a recipe from all meals' side recipe lists for a specific user.
        Used when a recipe is deleted.

        Args:
            recipe_id: ID of the recipe to remove
            user_id: ID of the user whose meals to update

        Returns:
            Number of meals updated
        """
        meals = self.get_meals_with_side_recipe(recipe_id, user_id)
        count = 0
        for meal in meals:
            if meal.remove_side_recipe(recipe_id):
                self.session.flush()
                count += 1
        return count

    # -- Recipe Lookup Methods -------------------------------------------------------------------
    def get_meals_using_recipe(self, recipe_id: int, user_id: int) -> List[Meal]:
        """
        Get all meals that use a specific recipe (as main or side) for a specific user.

        Args:
            recipe_id: ID of the recipe to search for
            user_id: ID of the user whose meals to search

        Returns:
            List of meals that use this recipe belonging to the user
        """
        # side_recipe_ids is a Python @property over a JSON Text column,
        # so we query the underlying _side_recipe_ids_json column with LIKE,
        # then filter in Python to eliminate partial-number false positives.
        stmt = select(Meal).where(
            Meal.user_id == user_id,
            or_(
                Meal.main_recipe_id == recipe_id,
                Meal._side_recipe_ids_json.like(f"%{recipe_id}%")
            )
        )
        result = self.session.execute(stmt)
        candidates = result.scalars().all()
        return [m for m in candidates if m.has_recipe(recipe_id)]

    # -- Validation Methods ----------------------------------------------------------------------
    def validate_meal_ids(self, meal_ids: List[int], user_id: int) -> List[int]:
        """
        Validate which meal IDs exist in the database and belong to the user.

        Args:
            meal_ids: List of meal IDs to validate
            user_id: ID of the user whose meals to validate

        Returns:
            List of valid meal IDs that exist and belong to the user
        """
        if not meal_ids:
            return []

        stmt = (
            select(Meal.id)
            .where(Meal.user_id == user_id)
            .where(Meal.id.in_(meal_ids))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def validate_recipe_ids(self, recipe_ids: List[int], user_id: int) -> List[int]:
        """
        Validate which recipe IDs exist in the database and belong to the user.

        Args:
            recipe_ids: List of recipe IDs to validate
            user_id: ID of the user whose recipes to validate

        Returns:
            List of valid recipe IDs that exist and belong to the user
        """
        if not recipe_ids:
            return []

        stmt = (
            select(Recipe.id)
            .where(Recipe.user_id == user_id)
            .where(Recipe.id.in_(recipe_ids))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    # -- Utility Methods -------------------------------------------------------------------------
    def count(self, user_id: int) -> int:
        """
        Count total number of meals for a specific user.

        Args:
            user_id: ID of the user whose meals to count

        Returns:
            Total count of meals belonging to the user
        """
        stmt = (
            select(func.count())
            .select_from(Meal)
            .where(Meal.user_id == user_id)
        )
        return self.session.execute(stmt).scalar() or 0
