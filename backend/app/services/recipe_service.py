"""app/core/services/recipe_service.py

RecipeService using SQLAlchemy repository pattern.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────

import logging
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..dtos.ingredient_dtos import IngredientCreateDTO
from ..dtos.meal_dtos import MealResponseDTO, RecipeDeletionImpactDTO
from ..dtos.recipe_dtos import (
    RecipeCardDTO,
    RecipeCreateDTO,
    RecipeFilterDTO,
    RecipeIngredientDTO,
    RecipeUpdateDTO)
from ..models.ingredient import Ingredient
from ..models.meal import Meal
from ..models.recipe import Recipe
from ..repositories.ingredient_repo import IngredientRepo
from ..repositories.meal_repo import MealRepo
from ..repositories.recipe_repo import RecipeRepo


# ── Exceptions ──────────────────────────────────────────────────────────────────────────────────────────────
class RecipeSaveError(Exception):
    pass

class RecipeNotFoundError(RecipeSaveError):
    """Raised when the recipe doesn't exist or isn't owned by the user."""


class DuplicateRecipeError(Exception):
    pass


# ── Recipe Service ──────────────────────────────────────────────────────────────────────────────────────────
class RecipeService:
    """Service layer for managing recipes and their ingredients."""

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the RecipeService with a database session and user ID.

        Args:
            session: SQLAlchemy database session (required).
            user_id: ID of the authenticated user (required for multi-tenant isolation).
        """
        self.session = session
        self.user_id = user_id
        # ensure ingredient repository is created with user_id before passing to recipe repository
        self.ingredient_repo = IngredientRepo(self.session, user_id)
        self.recipe_repo = RecipeRepo(self.session, self.ingredient_repo, user_id)
        self.meal_repo = MealRepo(self.session)

    # -- Shopping List Sync Helper ---------------------------------------------------------------
    def _sync_shopping_list_if_recipe_in_planner(self, recipe_id: int) -> None:
        """
        Sync shopping list if the recipe is used in any active planner entry.

        Args:
            recipe_id: ID of the recipe to check
        """
        from ..repositories.planner import PlannerRepo

        planner_repo = PlannerRepo(self.session)

        # Get meals that use this recipe (as main or side)
        meals_with_recipe = self.meal_repo.get_meals_using_recipe(recipe_id, self.user_id)
        if not meals_with_recipe:
            return

        # Check if any of those meals are in active planner entries
        for meal in meals_with_recipe:
            entries = planner_repo.get_by_meal_id(meal.id, self.user_id)
            active_entries = [e for e in entries if not e.is_completed and not e.is_cleared]
            if active_entries:
                # Found at least one active entry, sync and return
                from ..services.shopping import ShoppingService
                shopping_service = ShoppingService(self.session, self.user_id)
                shopping_service.sync_shopping_list()
                return

    def create_recipe_with_ingredients(self, recipe_dto: RecipeCreateDTO) -> Recipe:
        if self.recipe_repo.recipe_exists(
            name=recipe_dto.recipe_name,
            category=recipe_dto.recipe_category,
            user_id=self.user_id,
        ):
            raise DuplicateRecipeError(
                f"Recipe '{recipe_dto.recipe_name}' "
                f"in category '{recipe_dto.recipe_category}' already exists."
            )

        try:
            recipe = self.recipe_repo.persist_recipe_and_links(recipe_dto, self.user_id)
            self.session.commit()
            return recipe
        except SQLAlchemyError as err:
            self.session.rollback()
            raise RecipeSaveError(
                f"Unable to save recipe '{recipe_dto.recipe_name}': {err}"
            ) from err

    def resolve_ingredient(
        self, ing_dto: RecipeIngredientDTO
        ) -> Ingredient:
        """
        Resolve or create an Ingredient from an ingredient DTO.

        Args:
            ing_dto (RecipeIngredientDTO)

        Returns:
            Ingredient
        """
        if ing_dto.existing_ingredient_id:
            return self.ingredient_repo.get_by_id(ing_dto.existing_ingredient_id)

        dto = IngredientCreateDTO(
            ingredient_name=ing_dto.ingredient_name,
            ingredient_category=ing_dto.ingredient_category,
            quantity=ing_dto.quantity,
            unit=ing_dto.unit,
        )
        return self.ingredient_repo.get_or_create(dto)

    def list_filtered(self, filter_dto: RecipeFilterDTO) -> list[Recipe]:
        """
        List recipes based on filter criteria for the current user.

        Args:
            filter_dto (RecipeFilterDTO): Filter criteria for recipes.

        Returns:
            list[Recipe]: List of recipes matching the filter (owned by current user).
        """
        return self.recipe_repo.filter_recipes(filter_dto, self.user_id)

    def toggle_favorite(self, recipe_id: int) -> Recipe | None:
        """
        Toggle the favorite status of a recipe using the current session.

        Args:
            recipe_id (int): ID of the recipe to toggle.

        Returns:
            Optional[Recipe]: The updated recipe with new favorite status, or None if not found/owned.
        """
        # Use the repository bound to this service's session
        updated_recipe = self.recipe_repo.toggle_favorite(recipe_id, self.user_id)
        if not updated_recipe:
            return None
        # Favoriting a starter recipe makes it the user's; "Remove sample data" keeps it
        updated_recipe.is_sample = False
        # persist the change
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to toggle recipe {recipe_id} favorite status, rolling back: {e}")
            raise
        return updated_recipe

    def update_recipe_reference_image_path(self, recipe_id: int, image_path: str) -> Recipe | None:
        """
        Update a recipe's default image path.

        Args:
            recipe_id (int): ID of the recipe to update.
            image_path (str): New default image path to set.

        Returns:
            Recipe | None: The updated recipe or None if not found/owned.
        """
        try:
            recipe = self.recipe_repo.get_by_id(recipe_id, self.user_id)
            if not recipe:
                return None

            recipe.reference_image_path = image_path
            self.session.commit()
            logger.info(f"Updated recipe {recipe_id} default image path to: {image_path}")
            return recipe
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update recipe {recipe_id} default image path: {e}")
            raise

    def update_recipe_banner_image_path(self, recipe_id: int, image_path: str) -> Recipe | None:
        """
        Update a recipe's banner image path.

        Args:
            recipe_id (int): ID of the recipe to update.
            image_path (str): New banner image path to set.

        Returns:
            Recipe | None: The updated recipe or None if not found/owned.
        """
        try:
            recipe = self.recipe_repo.get_by_id(recipe_id, self.user_id)
            if not recipe:
                return None

            recipe.banner_image_path = image_path
            self.session.commit()
            logger.info(f"Updated recipe {recipe_id} banner image path to: {image_path}")
            return recipe
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update recipe {recipe_id} banner image path: {e}")
            raise

    def delete_recipe(self, recipe_id: int) -> bool:
        """
        Delete a recipe by ID.

        Before deletion:
        - Meals with this recipe as main will CASCADE delete
        - Meals with this recipe as a side will have it removed from their side_recipe_ids

        Returns:
            bool: True if deleted, False if not found/owned.
        """
        try:
            recipe = self.recipe_repo.get_by_id(recipe_id, self.user_id)
            if not recipe:
                return False

            # Clean up side_recipe_ids in affected meals before deletion
            # (Meals with this as main will CASCADE delete automatically)
            self.meal_repo.remove_side_recipe_from_all_meals(recipe_id, self.user_id)

            self.recipe_repo.delete_recipe(recipe)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to delete recipe {recipe_id}: {e}")
            raise

        # The recipe may have fed planned meals; drop its shopping items now
        self._resync_shopping_list()
        return True

    def _resync_shopping_list(self) -> None:
        """Best-effort shopping sync after a committed change (never fails the request)."""
        from .shopping import ShoppingService
        from .shopping.sync import discard_cached_shopping_rows

        # The delete cascaded (at the DB level) through meals, planner entries and
        # shopping contributions the session still holds; start the sync clean
        # so those dead rows can't collide with the ones it writes
        discard_cached_shopping_rows(self.session)
        try:
            ShoppingService(self.session, self.user_id).sync_shopping_list()
        except Exception:
            self.session.rollback()
            logger.exception("Shopping sync failed for user %s", self.user_id)

    def get_recipe_deletion_impact(self, recipe_id: int) -> RecipeDeletionImpactDTO:
        """
        Get the impact of deleting a recipe on meals.

        Returns information about:
        - meals_to_delete: Meals that will be deleted (recipe is their main_recipe_id)
        - meals_to_update: Meals that will have this recipe removed from sides

        Args:
            recipe_id: ID of the recipe to check

        Returns:
            RecipeDeletionImpactDTO with affected meals
        """
        try:
            meals_as_main = self.meal_repo.get_meals_by_main_recipe(recipe_id, self.user_id)
            meals_as_side = self.meal_repo.get_meals_with_side_recipe(recipe_id, self.user_id)

            meals_to_delete = [self._meal_to_response_dto(m) for m in meals_as_main]
            meals_to_update = [self._meal_to_response_dto(m) for m in meals_as_side]

            return RecipeDeletionImpactDTO(
                recipe_id=recipe_id,
                meals_to_delete=meals_to_delete,
                meals_to_update=meals_to_update,
                total_affected=len(meals_to_delete) + len(meals_to_update),
            )
        except SQLAlchemyError:
            return RecipeDeletionImpactDTO(
                recipe_id=recipe_id,
                meals_to_delete=[],
                meals_to_update=[],
                total_affected=0,
            )

    def _meal_to_response_dto(self, meal: Meal) -> MealResponseDTO:
        """Convert a Meal model to a response DTO."""
        return MealResponseDTO(
            id=meal.id,
            meal_name=meal.meal_name,
            main_recipe_id=meal.main_recipe_id,
            side_recipe_ids=meal.side_recipe_ids,
            is_saved=meal.is_saved,
            tags=meal.tags,
            created_at=meal.created_at.isoformat() if meal.created_at else None,
            main_recipe=RecipeCardDTO.from_recipe(meal.main_recipe),
        )

    def update_recipe(self, recipe_id: int, update_dto: RecipeUpdateDTO) -> Recipe:
        """
        Update an existing recipe and its ingredient links.

        Raises:
            RecipeSaveError: If recipe not found/owned or database error occurs.
        """
        try:
            updated_recipe = self.recipe_repo.update_recipe(recipe_id, update_dto, self.user_id)
            if not updated_recipe:
                raise RecipeNotFoundError(f"Recipe {recipe_id} not found.")
            # An edited starter recipe is the user's now; "Remove sample data" keeps it
            updated_recipe.is_sample = False
            self.session.commit()

            # Sync shopping list if recipe's ingredients changed and it's in planner
            if update_dto.ingredients is not None:
                self._sync_shopping_list_if_recipe_in_planner(recipe_id)

            return updated_recipe
        except SQLAlchemyError as err:
            self.session.rollback()
            raise RecipeSaveError(
                f"Unable to update recipe '{recipe_id}': {err}"
            ) from err

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        """
        Retrieve a single recipe by ID for the current user.

        Args:
            recipe_id (int): ID of the recipe to retrieve.

        Returns:
            Optional[Recipe]: The Recipe if found and owned by user, else None.
        """
        return self.recipe_repo.get_by_id(recipe_id, self.user_id)

    def get_last_cooked_date(self, recipe_id: int) -> datetime | None:
        """
        Get the most recent date a recipe was cooked.

        Args:
            recipe_id (int): ID of the recipe to check.

        Returns:
            datetime | None: The last cooked date, or None if never cooked or not owned.
        """
        return self.recipe_repo.get_last_cooked_date(recipe_id, self.user_id)
