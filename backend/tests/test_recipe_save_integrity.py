"""Save-path integrity: duplicate ingredients, input limits, meal tag/side validation."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dtos.meal_dtos import MealCreateDTO, MealUpdateDTO
from app.dtos.recipe_dtos import RecipeCreateDTO, RecipeIngredientDTO, RecipeUpdateDTO
from app.models.recipe import Recipe
from app.models.shopping_item import ShoppingItem
from app.services.meal import MealService
from app.services.recipe_service import RecipeService


def _ing(name: str, qty=None, unit=None, category="Pantry") -> RecipeIngredientDTO:
    return RecipeIngredientDTO(
        ingredient_name=name, ingredient_category=category, quantity=qty, unit=unit
    )


def _recipe(db_session, user_id: int, name: str) -> Recipe:
    recipe = Recipe(recipe_name=name, recipe_category="Mains", meal_type="Dinner", user_id=user_id)
    db_session.add(recipe)
    db_session.flush()
    return recipe


class TestDuplicateIngredients:
    def test_create_merges_repeated_ingredient(self, db_session, test_user):
        recipe = RecipeService(db_session, test_user.id).create_recipe_with_ingredients(
            RecipeCreateDTO(
                recipe_name="Pasta",
                recipe_category="Mains",
                ingredients=[_ing("Salt", 1, "tsp"), _ing("salt", 2, "tsp"), _ing("Pepper")],
            )
        )
        links = {ri.ingredient.ingredient_name.lower(): ri for ri in recipe.ingredients}
        assert len(recipe.ingredients) == 2
        assert links["salt"].quantity == 3

    def test_update_merges_repeated_ingredient(self, db_session, test_user):
        service = RecipeService(db_session, test_user.id)
        recipe = service.create_recipe_with_ingredients(
            RecipeCreateDTO(recipe_name="Soup", recipe_category="Mains", ingredients=[_ing("Salt")])
        )
        updated = service.update_recipe(
            recipe.id,
            RecipeUpdateDTO(ingredients=[_ing("Salt", 1, "tsp"), _ing("Salt", 1, "tbsp")]),
        )
        assert len(updated.ingredients) == 1
        # Different units can't be added up; the first listing wins
        assert (updated.ingredients[0].quantity, updated.ingredients[0].unit) == (1, "tsp")


class TestInputLimits:
    def test_overlong_ingredient_fields_rejected(self):
        with pytest.raises(ValidationError):
            _ing("x" * 201)
        with pytest.raises(ValidationError):
            _ing("Salt", 1, "u" * 51)
        with pytest.raises(ValidationError):
            _ing("Salt", -1)

    def test_overlong_recipe_name_rejected_on_create(self):
        with pytest.raises(ValidationError):
            RecipeCreateDTO(recipe_name="x" * 256, recipe_category="Mains")

    def test_aggregation_key_fits_its_column(self):
        assert len(ShoppingItem.make_aggregation_key("x" * 400, "mass")) <= 255


class TestMealValidation:
    def test_too_many_tags_is_a_validation_error(self):
        with pytest.raises(ValidationError):
            MealCreateDTO(meal_name="M", main_recipe_id=1, tags=[f"t{i}" for i in range(21)])
        with pytest.raises(ValidationError):
            MealUpdateDTO(tags=["x" * 51])

    def test_tags_are_normalized(self):
        dto = MealCreateDTO(meal_name="M", main_recipe_id=1, tags=[" Quick ", "quick", ""])
        assert dto.tags == ["quick"]

    def test_duplicate_and_main_side_ids_are_dropped(self, db_session, test_user):
        main = _recipe(db_session, test_user.id, "Main")
        side = _recipe(db_session, test_user.id, "Side")
        meal = MealService(db_session, test_user.id).create_meal(
            MealCreateDTO(
                meal_name="Dinner", main_recipe_id=main.id, side_recipe_ids=[side.id, side.id, main.id]
            )
        )
        assert meal.side_recipe_ids == [side.id]


class TestErrorHygiene:
    def test_recipe_save_db_error_is_not_leaked(self, db_session, test_user):
        from app.api import recipes as recipes_api
        from app.api.auth import get_current_user
        from app.database.db import get_session

        app = FastAPI()
        app.include_router(recipes_api.router, prefix="/api/recipes")
        user = MagicMock()
        user.id = test_user.id
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_session] = lambda: db_session

        original = RecipeService.create_recipe_with_ingredients

        def boom(self, dto):
            from app.services.recipe_service import RecipeSaveError

            raise RecipeSaveError("INSERT INTO recipe (secret_column) VALUES (...)")

        RecipeService.create_recipe_with_ingredients = boom
        try:
            resp = TestClient(app).post(
                "/api/recipes", json={"recipe_name": "X", "recipe_category": "Mains"}
            )
        finally:
            RecipeService.create_recipe_with_ingredients = original
        assert resp.status_code == 500
        assert "INSERT" not in resp.text
