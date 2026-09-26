"""app/services/meal/service.py

Core service logic for meal CRUD operations.
Handles creation, basic reads, updates, deletion, and DTO conversion.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...dtos.meal_dtos import (
    MealCreateDTO,
    MealResponseDTO,
    MealUpdateDTO,
    RecipeCardDTO,
)
from ...models.meal import Meal
from ...models.recipe import Recipe
from ...repositories.meal_repo import MealRepo
from ...repositories.planner import PlannerRepo
from ...repositories.recipe_repo import RecipeRepo


# -- Exceptions ----------------------------------------------------------------------------------
class MealSaveError(Exception):
    """Raised when a meal cannot be saved."""

    pass


class MealNotFoundError(Exception):
    """Raised when a meal is not found."""

    pass


class InvalidRecipeError(Exception):
    """Raised when a recipe ID is invalid."""

    pass


# -- Core Service --------------------------------------------------------------------------------
class MealServiceCore:
    """Core meal service with CRUD operations and business logic."""

    MAX_SIDE_RECIPES = 3

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the MealService with a database session and user ID.

        Args:
            session: SQLAlchemy database session (required).
            user_id: ID of the authenticated user (required for multi-tenant isolation).
        """
        self.session = session
        self.user_id = user_id
        self.repo = MealRepo(self.session)
        self.planner_repo = PlannerRepo(self.session)
        self.recipe_repo = RecipeRepo(self.session, user_id=user_id)

    # -- Shopping List Sync Helper ---------------------------------------------------------------
    def _sync_shopping_list_if_meal_in_planner(self, meal_id: int) -> None:
        """
        Sync shopping list if the meal is currently in the planner.

        Args:
            meal_id: ID of the meal to check
        """
        import logging

        logger = logging.getLogger(__name__)

        # Check if this meal has any active planner entries
        entries = self.planner_repo.get_by_meal_id(meal_id, self.user_id)
        active_entries = [e for e in entries if not e.is_completed and not e.is_cleared]

        logger.debug(
            f"Checking meal {meal_id} for shopping sync: {len(active_entries)} active entries"
        )

        if active_entries:
            try:
                from ..shopping import ShoppingService

                shopping_service = ShoppingService(self.session, self.user_id)
                shopping_service.sync_shopping_list()
                logger.debug(f"Shopping sync completed for meal {meal_id}")
            except Exception as e:
                logger.error(
                    f"Shopping sync failed for meal {meal_id}: {type(e).__name__}: {e}"
                )
                raise  # Re-raise so we see the error

    # -- Create Operations -----------------------------------------------------------------------
    def create_meal(self, create_dto: MealCreateDTO) -> MealResponseDTO:
        """
        Create a new meal for the current user.

        Args:
            create_dto: Data for creating the meal

        Returns:
            Created meal as DTO

        Raises:
            InvalidRecipeError: If recipe IDs are invalid
            MealSaveError: If the meal cannot be saved
        """
        try:
            # Validate main recipe exists and belongs to user
            valid_ids = self.repo.validate_recipe_ids(
                [create_dto.main_recipe_id], self.user_id
            )
            if create_dto.main_recipe_id not in valid_ids:
                raise InvalidRecipeError(
                    f"Main recipe ID {create_dto.main_recipe_id} does not exist"
                )

            # Validate side recipe IDs if provided
            side_ids = create_dto.side_recipe_ids or []
            if len(side_ids) > self.MAX_SIDE_RECIPES:
                raise InvalidRecipeError(
                    f"Maximum of {self.MAX_SIDE_RECIPES} side recipes allowed"
                )

            if side_ids:
                valid_side_ids = self.repo.validate_recipe_ids(side_ids, self.user_id)
                invalid_side_ids = [sid for sid in side_ids if sid not in valid_side_ids]
                if invalid_side_ids:
                    raise InvalidRecipeError(
                        f"Side recipe IDs {invalid_side_ids} do not exist"
                    )

            # Create the meal
            meal = Meal(
                meal_name=create_dto.meal_name,
                main_recipe_id=create_dto.main_recipe_id,
                is_saved=create_dto.is_saved or False,
            )
            meal.side_recipe_ids = side_ids
            meal.tags = create_dto.tags or []

            created_meal = self.repo.create_meal(meal, self.user_id)
            self.session.commit()

            # Refresh to get relationships
            created_meal = self.repo.get_by_id(created_meal.id, self.user_id)
            return self._meal_to_response_dto(created_meal)

        except (InvalidRecipeError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise MealSaveError(f"Failed to create meal: {e}") from e

    # -- Read Operations -------------------------------------------------------------------------
    def get_meal(self, meal_id: int) -> Optional[MealResponseDTO]:
        """
        Get a meal by ID for the current user.

        Args:
            meal_id: ID of the meal

        Returns:
            Meal as DTO or None if not found/not owned
        """
        try:
            meal = self.repo.get_by_id(meal_id, self.user_id)
            return self._meal_to_response_dto(meal) if meal else None
        except SQLAlchemyError:
            return None

    def get_all_meals(self) -> List[MealResponseDTO]:
        """
        Get all meals for the current user.

        Returns:
            List of all meals as DTOs
        """
        try:
            meals = self.repo.get_all(self.user_id)
            return [self._meal_to_response_dto(m) for m in meals]
        except SQLAlchemyError:
            return []

    # -- Update Operations -----------------------------------------------------------------------
    def update_meal(
        self, meal_id: int, update_dto: MealUpdateDTO
    ) -> Optional[MealResponseDTO]:
        """
        Update an existing meal for the current user.

        Args:
            meal_id: ID of the meal to update
            update_dto: Updated data

        Returns:
            Updated meal as DTO or None if not found/not owned

        Raises:
            InvalidRecipeError: If recipe IDs are invalid
            MealSaveError: If the update fails
        """
        try:
            meal = self.repo.get_by_id(meal_id, self.user_id)
            if not meal:
                return None

            # Update meal name if provided
            if update_dto.meal_name is not None:
                meal.meal_name = update_dto.meal_name

            # Update main recipe if provided
            if update_dto.main_recipe_id is not None:
                valid_ids = self.repo.validate_recipe_ids(
                    [update_dto.main_recipe_id], self.user_id
                )
                if update_dto.main_recipe_id not in valid_ids:
                    raise InvalidRecipeError(
                        f"Main recipe ID {update_dto.main_recipe_id} does not exist"
                    )
                meal.main_recipe_id = update_dto.main_recipe_id

            # Update side recipes if provided
            if update_dto.side_recipe_ids is not None:
                side_ids = update_dto.side_recipe_ids
                if len(side_ids) > self.MAX_SIDE_RECIPES:
                    raise InvalidRecipeError(
                        f"Maximum of {self.MAX_SIDE_RECIPES} side recipes allowed"
                    )
                if side_ids:
                    valid_side_ids = self.repo.validate_recipe_ids(side_ids, self.user_id)
                    invalid_side_ids = [
                        sid for sid in side_ids if sid not in valid_side_ids
                    ]
                    if invalid_side_ids:
                        raise InvalidRecipeError(
                            f"Side recipe IDs {invalid_side_ids} do not exist"
                        )
                meal.side_recipe_ids = side_ids

            # Update tags if provided
            if update_dto.tags is not None:
                meal.tags = update_dto.tags

            # An edited starter meal is the user's now; "Remove sample data" keeps it
            meal.is_sample = False
            updated_meal = self.repo.update(meal)
            self.session.commit()

            # Sync shopping list if recipe IDs changed
            if (
                update_dto.main_recipe_id is not None
                or update_dto.side_recipe_ids is not None
            ):
                self._sync_shopping_list_if_meal_in_planner(meal_id)

            # Refresh to get relationships
            updated_meal = self.repo.get_by_id(updated_meal.id, self.user_id)
            return self._meal_to_response_dto(updated_meal)

        except (InvalidRecipeError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise MealSaveError(f"Failed to update meal: {e}") from e

    def toggle_save(self, meal_id: int) -> Optional[MealResponseDTO]:
        """
        Toggle the saved status of a meal for the current user.

        When unsaved, the meal becomes transient and will be deleted
        when it leaves the planner.

        Args:
            meal_id: ID of the meal

        Returns:
            Updated meal as DTO or None if not found/not owned
        """
        try:
            meal = self.repo.get_by_id(meal_id, self.user_id)
            if not meal:
                return None

            meal.is_saved = not meal.is_saved
            self.repo.update(meal)
            self.session.commit()

            return self._meal_to_response_dto(meal)
        except SQLAlchemyError:
            self.session.rollback()
            return None

    # -- Delete Operations -----------------------------------------------------------------------
    def delete_meal(self, meal_id: int) -> bool:
        """
        Delete a meal for the current user.
        Note: This will CASCADE delete any planner entries referencing this meal.

        Args:
            meal_id: ID of the meal to delete

        Returns:
            True if deleted, False if not found/not owned
        """
        try:
            result = self.repo.delete(meal_id, self.user_id)
            self.session.commit()
            return result
        except SQLAlchemyError:
            self.session.rollback()
            return False

    # -- Helper Methods --------------------------------------------------------------------------
    def _meal_to_response_dto(self, meal: Meal) -> MealResponseDTO:
        """
        Convert a Meal model to a response DTO.

        Args:
            meal: Meal model

        Returns:
            MealResponseDTO with hydrated main_recipe, side_recipes, and computed stats
        """
        # Hydrate side recipes by fetching from database (filter by user_id for safety)
        side_recipes: List[RecipeCardDTO] = []
        side_ids = meal.side_recipe_ids
        if side_ids:
            # Fetch all side recipes in a single query, filtered by user
            recipes = (
                self.session.query(Recipe)
                .filter(Recipe.user_id == self.user_id)
                .filter(Recipe.id.in_(side_ids))
                .all()
            )
            # Create a lookup dict to preserve order
            recipe_lookup = {r.id: r for r in recipes}
            # Build the list in the same order as side_recipe_ids
            for recipe_id in side_ids:
                if recipe_id in recipe_lookup:
                    side_recipes.append(
                        RecipeCardDTO.from_recipe(recipe_lookup[recipe_id])
                    )

        # Get stats from main recipe only (recipe-level stats, not meal-level)
        total_cook_time = meal.main_recipe.total_time if meal.main_recipe else None
        servings = meal.main_recipe.servings if meal.main_recipe else None

        # Get cooking stats from main recipe history
        times_cooked = 0
        last_cooked = None
        if meal.main_recipe_id:
            times_cooked = self.recipe_repo.get_times_cooked(
                meal.main_recipe_id, self.user_id
            )
            last_cooked = self.recipe_repo.get_last_cooked_date(
                meal.main_recipe_id, self.user_id
            )

        return MealResponseDTO(
            id=meal.id,
            meal_name=meal.meal_name,
            main_recipe_id=meal.main_recipe_id,
            side_recipe_ids=meal.side_recipe_ids,
            is_saved=meal.is_saved,
            tags=meal.tags,
            created_at=meal.created_at.isoformat() if meal.created_at else None,
            main_recipe=RecipeCardDTO.from_recipe(meal.main_recipe),
            side_recipes=side_recipes,
            # Main recipe stats
            total_cook_time=total_cook_time,
            avg_servings=servings,
            times_cooked=times_cooked if times_cooked > 0 else None,
            last_cooked=last_cooked.isoformat() if last_cooked else None,
        )
