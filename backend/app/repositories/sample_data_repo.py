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
from ..models.recipe import Recipe
from ..models.recipe_ingredient import RecipeIngredient


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
