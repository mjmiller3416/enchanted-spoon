"""Build user context data for AI assistant prompts.

This module aggregates user data (recipes, meal plan, shopping list) into
structured data that can be used with the assistant's build_user_context_prompt().
"""

from typing import Dict, List
from sqlalchemy.orm import Session

from app.repositories.recipe_repo import RecipeRepo
from app.repositories.planner import PlannerRepo
from app.repositories.shopping import ShoppingRepo
from app.dtos.recipe_dtos import RecipeFilterDTO
from app.services.user_category_service import UserCategoryService

# Meal-planning catalog caps (keeps the planning prompt bounded for huge libraries)
MAX_CATALOG_RECIPES = 400
MAX_CATALOG_INGREDIENTS = 8


class UserContextBuilder:
    """Builds structured user context data for AI prompts."""

    def __init__(self, session: Session, user_id: int) -> None:
        """Initialize with database session and user ID."""
        self.session = session
        self.user_id = user_id
        self.recipe_repo = RecipeRepo(session, user_id=user_id)
        self.planner_repo = PlannerRepo(session)
        self.shopping_repo = ShoppingRepo(session, user_id)

    def build_context_data(
        self,
        include_ingredients: bool = False,
        include_shopping_list: bool = False,
    ) -> dict:
        """Build structured context data dict.

        This returns a dict that can be passed to build_user_context_prompt()
        in assistant/context.py.

        Args:
            include_ingredients: Whether to include recipe ingredients.
            include_shopping_list: Whether to include shopping list.

        Returns:
            Dict with saved_recipes, meal_plan, and optionally
            recipe_ingredients and shopping_list.
        """
        data: Dict[str, any] = {
            "saved_recipes": self._get_saved_recipes(),
            "meal_plan": self._get_meal_plan(),
            "allowed_categories": self._get_enabled_categories(),
        }

        if include_ingredients:
            data["recipe_ingredients"] = self._get_recipe_ingredients()

        if include_shopping_list:
            data["shopping_list"] = self._get_shopping_list()

        return data

    def _get_saved_recipes(self) -> List[dict]:
        """Get saved recipes limited to 30 (favorites + 20 recent).

        This prevents context window bloat while still providing useful data.
        """
        filter_dto = RecipeFilterDTO()
        all_recipes = self.recipe_repo.filter_recipes(filter_dto, self.user_id)

        if not all_recipes:
            return []

        # Sort by created_at desc (most recent first)
        # Handle both timezone-aware and naive datetimes
        all_recipes.sort(
            key=lambda r: r.created_at.replace(tzinfo=None) if r.created_at else None,
            reverse=True,
        )

        # Take all favorites + top 20 non-favorites
        favorites = [r for r in all_recipes if r.is_favorite]
        others = [r for r in all_recipes if not r.is_favorite][:20]

        # Combine and limit to ~30
        display_recipes = (favorites + others)[:30]

        return [
            {
                "name": r.recipe_name,
                "category": r.recipe_category,
                "meal_type": r.meal_type,
                "total_time": r.total_time,
                "is_favorite": r.is_favorite,
            }
            for r in display_recipes
        ]

    def _get_recipe_ingredients(self) -> Dict[str, List[str]]:
        """Get ingredients for each recipe (for ingredient-based queries)."""
        filter_dto = RecipeFilterDTO()
        recipes = self.recipe_repo.filter_recipes(filter_dto, self.user_id)
        result: Dict[str, List[str]] = {}

        for recipe in recipes:
            if recipe.ingredients:
                ingredients = [
                    ri.ingredient.ingredient_name
                    for ri in recipe.ingredients
                    if ri.ingredient
                ]
                if ingredients:
                    result[recipe.recipe_name] = ingredients

        return result

    def build_recipe_catalog(self) -> List[dict]:
        """Get the recipe library Genie plans meals from (favorites first, then newest).

        Unlike the saved-recipes summary this carries IDs and key ingredients, so
        the planner can match requests like "ground beef" and reference recipes
        exactly. Only loaded when Genie is actually asked to plan meals.

        Returns:
            List of {id, name, category, meal_type, total_time, is_favorite, ingredients}.
        """
        recipes = list(self.recipe_repo.filter_recipes(RecipeFilterDTO(), self.user_id))
        # Higher id = created later; avoids comparing mixed naive/aware datetimes
        recipes.sort(key=lambda r: (not r.is_favorite, -r.id))

        return [
            {
                "id": r.id,
                "name": r.recipe_name,
                "category": r.recipe_category,
                "meal_type": r.meal_type,
                "total_time": r.total_time,
                "is_favorite": r.is_favorite,
                "ingredients": [
                    ri.ingredient.ingredient_name for ri in r.ingredients if ri.ingredient
                ][:MAX_CATALOG_INGREDIENTS],
            }
            for r in recipes[:MAX_CATALOG_RECIPES]
        ]

    def _get_meal_plan(self) -> List[dict]:
        """Get current meal plan entries."""
        entries = self.planner_repo.get_incomplete_entries(self.user_id)

        return [
            {
                "meal_name": entry.meal.meal_name if entry.meal else "Unknown",
                "main_recipe_name": (
                    entry.meal.main_recipe.recipe_name
                    if entry.meal and entry.meal.main_recipe
                    else "Unknown"
                ),
            }
            for entry in entries
        ]

    def _get_enabled_categories(self) -> List[str]:
        """Get the user's enabled category values for recipe generation."""
        category_service = UserCategoryService(self.session, self.user_id)
        categories = category_service.get_all_categories(include_disabled=False)
        return [cat.value for cat in categories]

    def _get_shopping_list(self) -> dict:
        """Get shopping list split by have/need."""
        items = self.shopping_repo.get_all_shopping_items(self.user_id)
        return {
            "need": [i.ingredient_name for i in items if not i.have],
            "have": [i.ingredient_name for i in items if i.have],
        }

