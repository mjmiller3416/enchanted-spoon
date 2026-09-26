"""app/repositories/sample_data_repo.py

Data access for starter-pack (sample) content: lookups by the ``is_sample``
flag and cleanup of ingredients the starter pack left behind. Flushes only;
the service owns the transaction.
"""

from typing import Iterable, List, Set, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.ingredient import Ingredient
from ..models.meal import Meal
from ..models.planner_entry import PlannerEntry
from ..models.recipe import Recipe
from ..models.recipe_group import recipe_group_association
from ..models.recipe_history import RecipeHistory
from ..models.recipe_ingredient import RecipeIngredient

# Cloudinary folder a recipe's own uploaded/generated images live under
RECIPE_IMAGE_FOLDER = "meal-genie/recipes"


class SampleDataRepo:
    """Repository for querying and cleaning up a user's sample content."""

    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id

    # -- Reads -----------------------------------------------------------------------------------
    def count_sample_recipes(self) -> int:
        stmt = select(func.count(Recipe.id)).where(
            Recipe.user_id == self.user_id, Recipe.is_sample.is_(True)
        )
        return self.session.execute(stmt).scalar_one()

    def count_sample_meals(self) -> int:
        stmt = select(func.count(Meal.id)).where(
            Meal.user_id == self.user_id, Meal.is_sample.is_(True)
        )
        return self.session.execute(stmt).scalar_one()

    def get_sample_recipes(self) -> List[Recipe]:
        stmt = select(Recipe).where(
            Recipe.user_id == self.user_id, Recipe.is_sample.is_(True)
        )
        return list(self.session.execute(stmt).scalars().unique().all())

    def get_sample_meals(self) -> List[Meal]:
        stmt = select(Meal).where(Meal.user_id == self.user_id, Meal.is_sample.is_(True))
        return list(self.session.execute(stmt).scalars().unique().all())

    def get_recipe_ids_used_by_user_meals(self) -> Set[int]:
        """Recipe IDs referenced (as main or side) by the user's own, non-sample meals."""
        stmt = select(Meal).where(Meal.user_id == self.user_id, Meal.is_sample.is_(False))
        used: Set[int] = set()
        for meal in self.session.execute(stmt).scalars().unique().all():
            used.update(meal.get_all_recipe_ids())
        return used

    def get_cooked_sample_meal_ids(self) -> Set[int]:
        """Sample meals with a completed planner entry (their history feeds the streak)."""
        stmt = (
            select(PlannerEntry.meal_id)
            .join(Meal, PlannerEntry.meal_id == Meal.id)
            .where(
                Meal.user_id == self.user_id,
                Meal.is_sample.is_(True),
                PlannerEntry.is_completed.is_(True),
            )
            .distinct()
        )
        return set(self.session.execute(stmt).scalars().all())

    def get_sample_recipe_ids_with_activity(self) -> Set[int]:
        """
        Sample recipes the user has made their own without editing them:
        cooked, filed in a group, or given their own image. (Favoriting
        clears ``is_sample`` directly, since the pack ships pre-favorited.)
        """
        sample = select(Recipe.id).where(
            Recipe.user_id == self.user_id, Recipe.is_sample.is_(True)
        )
        active: Set[int] = set()
        active.update(
            self.session.execute(
                select(RecipeHistory.recipe_id).where(RecipeHistory.recipe_id.in_(sample))
            ).scalars()
        )
        active.update(
            self.session.execute(
                select(recipe_group_association.c.recipe_id).where(
                    recipe_group_association.c.recipe_id.in_(sample)
                )
            ).scalars()
        )
        for recipe in self.get_sample_recipes():
            own_folder = f"{RECIPE_IMAGE_FOLDER}/{recipe.image_key}/"
            if any(
                path and own_folder in path
                for path in (recipe.reference_image_path, recipe.banner_image_path)
            ):
                active.add(recipe.id)
        return active

    # -- Writes ----------------------------------------------------------------------------------
    def delete_meal(self, meal: Meal) -> None:
        """Delete a meal (planner entries cascade)."""
        self.session.delete(meal)
        self.session.flush()

    def delete_recipe(self, recipe: Recipe) -> None:
        """Delete a recipe (ingredient links, history, contributions cascade)."""
        self.session.delete(recipe)
        self.session.flush()

    def delete_unused_ingredients(self, keys: Iterable[Tuple[str, str]]) -> int:
        """
        Delete the user's ingredients matching ``(lowercased name, category)`` keys
        that no recipe links to anymore.

        Returns:
            Number of ingredients deleted.
        """
        wanted = set(keys)
        if not wanted:
            return 0

        linked = select(RecipeIngredient.ingredient_id)
        stmt = select(Ingredient).where(
            Ingredient.user_id == self.user_id,
            Ingredient.id.not_in(linked),
        )
        deleted = 0
        for ingredient in self.session.execute(stmt).scalars().unique().all():
            key = (ingredient.ingredient_name.lower(), ingredient.ingredient_category)
            if key in wanted:
                self.session.delete(ingredient)
                deleted += 1
        self.session.flush()
        return deleted
