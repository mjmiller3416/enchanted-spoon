"""app/services/sample_data/service.py

Seeds the starter pack into an account and removes it again.

Starter content is flagged ``is_sample``. Editing a sample recipe or meal
clears the flag (see RecipeService / MealService), so "Remove sample data"
only deletes content the user never made their own.
"""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...dtos.recipe_dtos import RecipeCreateDTO, RecipeIngredientDTO
from ...dtos.sample_data_dtos import (
    SampleDataRemovalResultDTO,
    SampleDataSeedResultDTO,
    SampleDataStatusDTO,
)
from ...models.meal import Meal
from ...models.recipe import Recipe
from ...repositories.ingredient_repo import IngredientRepo
from ...repositories.meal_repo import MealRepo
from ...repositories.planner import MAX_PLANNER_ENTRIES, PlannerRepo
from ...repositories.recipe_repo import RecipeRepo
from ...repositories.sample_data_repo import SampleDataRepo
from .starter_pack import (
    STARTER_MEALS,
    STARTER_RECIPES,
    StarterRecipe,
    recipe_fields,
    starter_ingredient_keys,
)


# -- Exceptions ----------------------------------------------------------------------------------
class SampleDataError(Exception):
    """Raised when sample content cannot be seeded or removed."""


class SampleDataAlreadyPresentError(Exception):
    """Raised when seeding an account that still has sample content."""


# -- Service -------------------------------------------------------------------------------------
class SampleDataService:
    """Service for the starter pack shown to new accounts during onboarding."""

    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id
        self.repo = SampleDataRepo(session, user_id)
        self.recipe_repo = RecipeRepo(session, IngredientRepo(session, user_id), user_id)
        self.meal_repo = MealRepo(session)
        self.planner_repo = PlannerRepo(session)

    # -- Status ----------------------------------------------------------------------------------
    def get_status(self) -> SampleDataStatusDTO:
        recipe_count = self.repo.count_sample_recipes()
        meal_count = self.repo.count_sample_meals()
        return SampleDataStatusDTO(
            has_sample_data=recipe_count > 0 or meal_count > 0,
            recipe_count=recipe_count,
            meal_count=meal_count,
        )

    # -- Seed ------------------------------------------------------------------------------------
    def seed(self) -> SampleDataSeedResultDTO:
        """
        Add the starter pack: recipes, saved meals, planner entries, and the
        shopping list those entries produce.

        Recipes whose name+category the user already has are skipped (along
        with meals built on them), and planner entries stop at capacity, so
        this is safe to run on an existing account.

        Raises:
            SampleDataAlreadyPresentError: If the account still has sample content.
            SampleDataError: If the database write fails.
        """
        if self.get_status().has_sample_data:
            raise SampleDataAlreadyPresentError("Sample data is already in this account.")

        try:
            recipes = self._create_recipes()
            meals, planned = self._create_meals(recipes)
            entries = self._plan_meals(planned)
            self.session.commit()
        except SQLAlchemyError as err:
            self.session.rollback()
            raise SampleDataError(f"Unable to add sample data: {err}") from err

        if entries:
            self._sync_shopping_list()

        return SampleDataSeedResultDTO(
            recipes_created=len(recipes),
            meals_created=len(meals),
            planner_entries_created=entries,
        )

    def _create_recipes(self) -> dict[str, Recipe]:
        created: dict[str, Recipe] = {}
        for spec in STARTER_RECIPES:
            if self.recipe_repo.recipe_exists(
                name=spec["recipe_name"],
                category=spec["recipe_category"],
                user_id=self.user_id,
            ):
                continue
            recipe = self.recipe_repo.persist_recipe_and_links(self._to_create_dto(spec), self.user_id)
            recipe.is_sample = True
            recipe.is_favorite = spec.get("is_favorite", False)
            created[spec["recipe_name"]] = recipe
        self.session.flush()
        return created

    @staticmethod
    def _to_create_dto(spec: StarterRecipe) -> RecipeCreateDTO:
        return RecipeCreateDTO(
            **recipe_fields(spec),
            ingredients=[
                RecipeIngredientDTO(
                    ingredient_name=name,
                    ingredient_category=category,
                    quantity=quantity,
                    unit=unit,
                )
                for name, quantity, unit, category in spec["ingredients"]
            ],
        )

    def _create_meals(self, recipes: dict[str, Recipe]) -> tuple[list[Meal], list[tuple[int, Meal]]]:
        meals: list[Meal] = []
        planned: list[tuple[int, Meal]] = []
        for spec in STARTER_MEALS:
            main = recipes.get(spec["main"])
            if main is None:
                continue
            meal = Meal(meal_name=spec["meal_name"], main_recipe_id=main.id, is_saved=True)
            meal.side_recipe_ids = [recipes[s].id for s in spec["sides"] if s in recipes]
            meal.tags = spec["tags"]
            meal.is_sample = True
            self.meal_repo.create_meal(meal, self.user_id)
            meals.append(meal)
            if spec["planned"] is not None:
                planned.append((spec["planned"], meal))
        return meals, planned

    def _plan_meals(self, planned: list[tuple[int, Meal]]) -> int:
        room = MAX_PLANNER_ENTRIES - self.planner_repo.count_incomplete(self.user_id)
        added = 0
        for _order, meal in sorted(planned, key=lambda item: item[0]):
            if added >= room:
                break
            self.planner_repo.add_entry(meal.id, self.user_id)
            added += 1
        return added

    # -- Remove ----------------------------------------------------------------------------------
    def remove(self) -> SampleDataRemovalResultDTO:
        """
        Delete untouched sample meals and recipes, their planner entries, and
        starter ingredients nothing else uses, then rebuild the shopping list.

        A sample recipe that one of the user's own meals still uses, or that
        they've favorited, cooked, grouped, or given their own image, is kept
        and becomes a regular recipe; a sample meal they've cooked is kept too.

        Raises:
            SampleDataError: If the database write fails.
        """
        try:
            # A cooked sample meal is part of the user's history (streak,
            # "last cooked"): keep it as their own instead of deleting it
            cooked = self.repo.get_cooked_sample_meal_ids()
            meals_removed = 0
            for meal in self.repo.get_sample_meals():
                if meal.id in cooked:
                    meal.is_sample = False
                    continue
                self.repo.delete_meal(meal)
                meals_removed += 1
            self.session.flush()

            in_use = (
                self.repo.get_recipe_ids_used_by_user_meals()
                | self.repo.get_sample_recipe_ids_with_activity()
            )
            removed = kept = 0
            for recipe in self.repo.get_sample_recipes():
                if recipe.id in in_use:
                    recipe.is_sample = False
                    kept += 1
                    continue
                self.meal_repo.remove_side_recipe_from_all_meals(recipe.id, self.user_id)
                self.repo.delete_recipe(recipe)
                removed += 1

            self.repo.delete_unused_ingredients(starter_ingredient_keys())
            self.session.commit()
        except SQLAlchemyError as err:
            self.session.rollback()
            raise SampleDataError(f"Unable to remove sample data: {err}") from err

        self._sync_shopping_list()

        return SampleDataRemovalResultDTO(
            recipes_removed=removed,
            meals_removed=meals_removed,
            recipes_kept=kept,
        )

    # -- Helpers ---------------------------------------------------------------------------------
    def _sync_shopping_list(self) -> None:
        from ..shopping import ShoppingService

        ShoppingService(self.session, self.user_id).sync_shopping_list()
