"""Tests for the onboarding starter pack (SampleDataService + signup hook)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dtos.meal_dtos import MealCreateDTO, MealUpdateDTO
from app.dtos.recipe_dtos import RecipeUpdateDTO
from app.models.ingredient import Ingredient
from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.shopping_item import ShoppingItem
from app.models.user import User
from app.services.meal import MealService
from app.services.recipe_service import RecipeService
from app.services.sample_data import SampleDataAlreadyPresentError, SampleDataService
from app.services.sample_data.starter_pack import STARTER_MEALS, STARTER_RECIPES
from app.services.user_service import UserService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recipes(session: Session, user_id: int) -> list[Recipe]:
    return list(session.execute(select(Recipe).where(Recipe.user_id == user_id)).scalars().unique())


def _meals(session: Session, user_id: int) -> list[Meal]:
    return list(session.execute(select(Meal).where(Meal.user_id == user_id)).scalars().unique())


def _entries(session: Session, user_id: int) -> list[PlannerEntry]:
    return list(
        session.execute(select(PlannerEntry).where(PlannerEntry.user_id == user_id)).scalars().unique()
    )


def _shopping(session: Session, user_id: int) -> list[ShoppingItem]:
    return list(
        session.execute(select(ShoppingItem).where(ShoppingItem.user_id == user_id)).scalars().unique()
    )


def _ingredients(session: Session, user_id: int) -> list[Ingredient]:
    return list(
        session.execute(select(Ingredient).where(Ingredient.user_id == user_id)).scalars().unique()
    )


@pytest.fixture()
def service(db_session: Session, test_user: User) -> SampleDataService:
    return SampleDataService(db_session, test_user.id)


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

class TestSeed:
    def test_seeds_full_kitchen(self, db_session, test_user, service):
        result = service.seed()

        planned = [m for m in STARTER_MEALS if m["planned"] is not None]
        assert result.recipes_created == len(STARTER_RECIPES)
        assert result.meals_created == len(STARTER_MEALS)
        assert result.planner_entries_created == len(planned)

        recipes = _recipes(db_session, test_user.id)
        assert len(recipes) == len(STARTER_RECIPES)
        assert all(r.is_sample for r in recipes)
        assert any(r.is_favorite for r in recipes)
        assert all(r.ingredients for r in recipes)

        meals = _meals(db_session, test_user.id)
        assert all(m.is_sample and m.is_saved for m in meals)

        entries = sorted(_entries(db_session, test_user.id), key=lambda e: e.position)
        assert [e.meal.meal_name for e in entries] == [
            m["meal_name"] for m in sorted(planned, key=lambda m: m["planned"])
        ]
        assert not any(e.is_completed for e in entries)

        # Planner entries build the shopping list
        assert _shopping(db_session, test_user.id)

    def test_status_reports_sample_data(self, service):
        assert service.get_status().has_sample_data is False
        service.seed()
        status = service.get_status()
        assert status.has_sample_data is True
        assert status.recipe_count == len(STARTER_RECIPES)
        assert status.meal_count == len(STARTER_MEALS)

    def test_seeding_twice_is_rejected(self, service):
        service.seed()
        with pytest.raises(SampleDataAlreadyPresentError):
            service.seed()

    def test_skips_recipes_the_user_already_has(self, db_session, test_user, service):
        tacos = next(r for r in STARTER_RECIPES if r["recipe_name"] == "Weeknight Beef Tacos")
        db_session.add(Recipe(
            recipe_name=tacos["recipe_name"],
            recipe_category=tacos["recipe_category"],
            meal_type="dinner",
            user_id=test_user.id,
        ))
        db_session.flush()

        result = service.seed()

        assert result.recipes_created == len(STARTER_RECIPES) - 1
        # Taco Night is built on the skipped recipe, so it is skipped too
        assert "Taco Night" not in {m.meal_name for m in _meals(db_session, test_user.id)}

    def test_respects_planner_capacity(self, db_session, test_user, service, monkeypatch):
        import app.services.sample_data.service as sample_service

        monkeypatch.setattr(sample_service, "MAX_PLANNER_ENTRIES", 1)
        result = service.seed()
        assert result.planner_entries_created == 1

    def test_is_isolated_per_user(self, db_session, test_user, second_user, service):
        service.seed()
        assert _recipes(db_session, second_user.id) == []
        assert SampleDataService(db_session, second_user.id).get_status().has_sample_data is False


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------

class TestRemove:
    def test_removes_everything_untouched(self, db_session, test_user, service):
        service.seed()
        result = service.remove()

        assert result.recipes_removed == len(STARTER_RECIPES)
        assert result.meals_removed == len(STARTER_MEALS)
        assert result.recipes_kept == 0
        assert _recipes(db_session, test_user.id) == []
        assert _meals(db_session, test_user.id) == []
        assert _entries(db_session, test_user.id) == []
        assert _shopping(db_session, test_user.id) == []
        assert _ingredients(db_session, test_user.id) == []
        assert service.get_status().has_sample_data is False

    def test_keeps_user_content(self, db_session, test_user, service):
        own = Recipe(recipe_name="Grandma's Chili", recipe_category="american",
                     meal_type="dinner", user_id=test_user.id)
        db_session.add(own)
        db_session.flush()

        service.seed()
        service.remove()

        assert [r.recipe_name for r in _recipes(db_session, test_user.id)] == ["Grandma's Chili"]

    def test_edited_recipe_is_kept(self, db_session, test_user, service):
        service.seed()
        pancakes = next(r for r in _recipes(db_session, test_user.id)
                        if r.recipe_name == "Fluffy Buttermilk Pancakes")

        RecipeService(db_session, test_user.id).update_recipe(
            pancakes.id, RecipeUpdateDTO(notes="Add blueberries!")
        )
        result = service.remove()

        assert result.recipes_removed == len(STARTER_RECIPES) - 1
        remaining = _recipes(db_session, test_user.id)
        assert [r.recipe_name for r in remaining] == ["Fluffy Buttermilk Pancakes"]
        assert remaining[0].is_sample is False
        # Its ingredients survive; unused starter ingredients do not
        assert {i.ingredient_name for i in _ingredients(db_session, test_user.id)} == {
            name for name, *_ in next(
                r for r in STARTER_RECIPES if r["recipe_name"] == "Fluffy Buttermilk Pancakes"
            )["ingredients"]
        }

    def test_edited_meal_and_its_recipes_are_kept(self, db_session, test_user, service):
        service.seed()
        taco_night = next(m for m in _meals(db_session, test_user.id) if m.meal_name == "Taco Night")

        MealService(db_session, test_user.id).update_meal(
            taco_night.id, MealUpdateDTO(meal_name="Taco Tuesday")
        )
        result = service.remove()

        assert result.meals_removed == len(STARTER_MEALS) - 1
        assert result.recipes_kept == 2  # tacos + cilantro lime rice
        assert [m.meal_name for m in _meals(db_session, test_user.id)] == ["Taco Tuesday"]
        # Its planner entry stays, and so does its part of the shopping list
        assert len(_entries(db_session, test_user.id)) == 1
        assert _shopping(db_session, test_user.id)

    def test_user_meal_using_sample_recipe_survives(self, db_session, test_user, service):
        service.seed()
        salad = next(r for r in _recipes(db_session, test_user.id)
                     if r.recipe_name == "Simple Green Salad")
        own = Recipe(recipe_name="Steak Frites", recipe_category="french",
                     meal_type="dinner", user_id=test_user.id)
        db_session.add(own)
        db_session.flush()
        MealService(db_session, test_user.id).create_meal(
            MealCreateDTO(meal_name="Steak Night", main_recipe_id=own.id, side_recipe_ids=[salad.id])
        )

        result = service.remove()

        assert result.recipes_kept == 1
        steak_night = next(m for m in _meals(db_session, test_user.id) if m.meal_name == "Steak Night")
        assert steak_night.side_recipe_ids == [salad.id]


# ---------------------------------------------------------------------------
# Signup hook
# ---------------------------------------------------------------------------

class TestSignupSeeding:
    def test_new_user_gets_starter_pack(self, db_session, monkeypatch):
        monkeypatch.delenv("SEED_STARTER_CONTENT", raising=False)
        user = UserService(db_session).get_or_create_from_clerk("clerk_new", "new@example.com")

        assert len(_recipes(db_session, user.id)) == len(STARTER_RECIPES)
        assert _entries(db_session, user.id)

    def test_returning_user_is_not_reseeded(self, db_session, monkeypatch):
        monkeypatch.delenv("SEED_STARTER_CONTENT", raising=False)
        service = UserService(db_session)
        user = service.get_or_create_from_clerk("clerk_new", "new@example.com")
        SampleDataService(db_session, user.id).remove()

        service.get_or_create_from_clerk("clerk_new", "new@example.com")
        assert _recipes(db_session, user.id) == []

    def test_can_be_disabled(self, db_session, monkeypatch):
        monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
        user = UserService(db_session).get_or_create_from_clerk("clerk_new", "new@example.com")
        assert _recipes(db_session, user.id) == []

    def test_seed_failure_does_not_block_signup(self, db_session, monkeypatch):
        monkeypatch.delenv("SEED_STARTER_CONTENT", raising=False)

        def boom(self):
            raise RuntimeError("seed failed")

        monkeypatch.setattr(SampleDataService, "seed", boom)
        user = UserService(db_session).get_or_create_from_clerk("clerk_new", "new@example.com")

        assert user.id is not None
        assert db_session.get(User, user.id).email == "new@example.com"
