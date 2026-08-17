"""Tests for the Hearth wall-display meal integration.

Covers the contract DTO mappers (pure) and the read pipeline the
``/api/hearth/meals`` endpoints run: planner → plan rows, and
meal + recipes → a meal card with ingredients and steps. Auth for these
endpoints is the shared ``get_integration_user`` dependency, already covered by
``test_shopping_external_ingest``.
"""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.dtos.hearth_dtos import (
    HearthMealPlanDTO,
    _steps_from_directions,
    hearth_recipe_from_response,
    planned_meal_from_entry,
)
from app.dtos.planner_dtos import PlannerEntryResponseDTO
from app.dtos.recipe_dtos import (
    RecipeCardDTO,
    RecipeIngredientResponseDTO,
    RecipeResponseDTO,
)
from app.models.meal import Meal
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.user import User
from app.services.meal import MealService
from app.services.planner import PlannerService
from app.services.recipe_service import RecipeService


# ---------------------------------------------------------------------------
# Pure mapper: directions → steps
# ---------------------------------------------------------------------------

class TestStepsFromDirections:
    def test_none_yields_empty(self):
        assert _steps_from_directions(None) == []

    def test_empty_string_yields_empty(self):
        assert _steps_from_directions("   ") == []

    def test_splits_on_newlines_and_trims(self):
        steps = _steps_from_directions("Boil water.\n  Add pasta.  \n\nDrain.")
        assert steps == ["Boil water.", "Add pasta.", "Drain."]

    def test_single_paragraph_is_one_step(self):
        steps = _steps_from_directions("Mix everything and bake until golden.")
        assert steps == ["Mix everything and bake until golden."]


# ---------------------------------------------------------------------------
# Pure mapper: recipe response → card recipe
# ---------------------------------------------------------------------------

class TestHearthRecipeFromResponse:
    def _response(self, **overrides) -> RecipeResponseDTO:
        data = dict(
            id=7,
            recipe_name="Test Pasta",
            recipe_category="Italian",
            meal_type="Dinner",
            directions="Step 1.\nStep 2.",
            servings=4,
            prep_time=10,
            cook_time=20,
            total_time=30,
            difficulty="Easy",
            notes="Salt the water.",
            banner_image_path="https://img.example/banner.jpg",
            ingredients=[
                RecipeIngredientResponseDTO(
                    id=1,
                    ingredient_name="Spaghetti",
                    ingredient_category="Pasta",
                    quantity=8.0,
                    unit="oz",
                )
            ],
        )
        data.update(overrides)
        return RecipeResponseDTO(**data)

    def test_maps_core_fields_and_role(self):
        card = hearth_recipe_from_response(self._response(), "main")
        assert card.id == 7
        assert card.name == "Test Pasta"
        assert card.role == "main"
        assert card.total_time == 30
        assert card.notes == "Salt the water."

    def test_maps_ingredients(self):
        card = hearth_recipe_from_response(self._response(), "side")
        assert len(card.ingredients) == 1
        ing = card.ingredients[0]
        assert ing.name == "Spaghetti"
        assert ing.quantity == 8.0
        assert ing.unit == "oz"
        assert ing.category == "Pasta"

    def test_steps_parsed_from_directions(self):
        card = hearth_recipe_from_response(self._response(), "main")
        assert card.steps == ["Step 1.", "Step 2."]

    def test_image_falls_back_to_reference_when_no_banner(self):
        card = hearth_recipe_from_response(
            self._response(banner_image_path=None, reference_image_path="ref.jpg"),
            "main",
        )
        assert card.image_url == "ref.jpg"


# ---------------------------------------------------------------------------
# Pure mapper: planner entry → plan row
# ---------------------------------------------------------------------------

class TestPlannedMealFromEntry:
    def _entry(self, **overrides) -> PlannerEntryResponseDTO:
        data = dict(
            id=100,
            meal_id=55,
            position=2,
            is_completed=False,
            scheduled_date="2026-08-18",
            meal_name="Taco Night",
            side_recipe_ids=[9, 10],
            main_recipe=RecipeCardDTO(
                id=9, recipe_name="Beef Tacos", total_time=25,
                banner_image_path="https://img.example/tacos.jpg",
            ),
        )
        data.update(overrides)
        return PlannerEntryResponseDTO(**data)

    def test_maps_row_fields(self):
        row = planned_meal_from_entry(self._entry())
        assert row.entry_id == 100
        assert row.meal_id == 55
        assert row.meal_name == "Taco Night"
        assert row.position == 2
        assert row.scheduled_date == "2026-08-18"
        assert row.side_dish_count == 2
        assert row.main_recipe_name == "Beef Tacos"
        assert row.total_time == 25
        assert row.image_url == "https://img.example/tacos.jpg"

    def test_falls_back_to_main_recipe_name_when_meal_name_missing(self):
        row = planned_meal_from_entry(self._entry(meal_name=None))
        assert row.meal_name == "Beef Tacos"

    def test_handles_missing_main_recipe(self):
        row = planned_meal_from_entry(
            self._entry(meal_name="Leftovers", main_recipe=None, side_recipe_ids=[])
        )
        assert row.meal_name == "Leftovers"
        assert row.main_recipe_name is None
        assert row.total_time is None
        assert row.side_dish_count == 0


# ---------------------------------------------------------------------------
# Read pipeline: services → contract DTOs (what the endpoints run)
# ---------------------------------------------------------------------------

def _add_ingredient_to_recipe(
    session: Session, recipe: Recipe, ingredient_id: int, quantity: float, unit: str
) -> None:
    session.add(
        RecipeIngredient(
            recipe_id=recipe.id, ingredient_id=ingredient_id, quantity=quantity, unit=unit
        )
    )
    session.flush()


class TestMealPlanPipeline:
    def test_plan_includes_seeded_entry(
        self, db_session: Session, test_user: User, sample_planner_entry
    ):
        entries = PlannerService(db_session, test_user.id).get_all_entries()
        plan = HearthMealPlanDTO(meals=[planned_meal_from_entry(e) for e in entries])

        assert len(plan.meals) == 1
        row = plan.meals[0]
        assert row.meal_id == sample_planner_entry.meal_id
        assert row.meal_name == "Test Meal"

    def test_plan_is_scoped_to_integration_user(
        self, db_session: Session, test_user: User, second_user: User, sample_planner_entry
    ):
        # The integration user has one entry; a different user sees none.
        others = PlannerService(db_session, second_user.id).get_all_entries()
        assert others == []

    def test_scheduled_date_surfaces_on_row(
        self, db_session: Session, test_user: User, sample_planner_entry
    ):
        sample_planner_entry.scheduled_date = date(2026, 8, 18)
        db_session.flush()

        entries = PlannerService(db_session, test_user.id).get_all_entries()
        row = planned_meal_from_entry(entries[0])
        assert row.scheduled_date == "2026-08-18"


class TestMealCardPipeline:
    def test_card_composes_meal_and_recipe_detail(
        self,
        db_session: Session,
        test_user: User,
        sample_meal: Meal,
        sample_recipe: Recipe,
        sample_ingredient,
    ):
        _add_ingredient_to_recipe(
            db_session, sample_recipe, sample_ingredient.id, quantity=8.0, unit="oz"
        )

        meal = MealService(db_session, test_user.id).get_meal(sample_meal.id)
        assert meal is not None

        recipe_service = RecipeService(db_session, test_user.id)
        main = recipe_service.get_recipe(meal.main_recipe_id)
        card_recipe = hearth_recipe_from_response(
            RecipeResponseDTO.from_recipe(main), "main"
        )

        assert card_recipe.name == "Test Pasta"
        assert card_recipe.role == "main"
        # directions from the sample_recipe fixture: two lines → two steps
        assert card_recipe.steps == ["Step 1: Boil water.", "Step 2: Cook pasta."]
        assert [i.name for i in card_recipe.ingredients] == ["Spaghetti"]
        assert card_recipe.ingredients[0].unit == "oz"

    def test_missing_meal_returns_none_from_service(
        self, db_session: Session, test_user: User
    ):
        assert MealService(db_session, test_user.id).get_meal(999999) is None
