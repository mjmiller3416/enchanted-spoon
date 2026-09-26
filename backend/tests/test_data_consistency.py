"""Consistency fixes: sample-data removal keeps used content, shopping resyncs
after deletes, seeded settings rows persist, and planner positions increase."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.recipe_group import RecipeGroup
from app.models.shopping_item import ShoppingItem
from app.models.user_category import UserCategory
from app.repositories.planner.entry_repo import PlannerEntryRepo
from app.services.meal import MealService
from app.services.planner import PlannerService
from app.services.recipe_service import RecipeService
from app.services.sample_data import SampleDataService
from app.services.user_category_service import UserCategoryService


def _sample_recipes(session: Session, user_id: int) -> list[Recipe]:
    return list(
        session.execute(
            select(Recipe).where(Recipe.user_id == user_id, Recipe.is_sample.is_(True))
        ).scalars().unique()
    )


def _recipe_items(session: Session, user_id: int) -> list[ShoppingItem]:
    return list(
        session.execute(
            select(ShoppingItem).where(
                ShoppingItem.user_id == user_id, ShoppingItem.source == "recipe"
            )
        ).scalars()
    )


class TestSampleRemovalKeepsUsedContent:
    def test_favorited_grouped_and_cooked_content_survives(self, db_session, test_user):
        uid = test_user.id
        SampleDataService(db_session, uid).seed()
        recipes = _sample_recipes(db_session, uid)
        unfavorited = next(r for r in recipes if not r.is_favorite)
        grouped = next(r for r in recipes if r is not unfavorited and not r.is_favorite)

        RecipeService(db_session, uid).toggle_favorite(unfavorited.id)
        group = RecipeGroup(name="Keepers", user_id=uid)
        group.recipes.append(grouped)
        db_session.add(group)

        entry = db_session.execute(
            select(PlannerEntry).where(PlannerEntry.user_id == uid)
        ).scalars().first()
        cooked_meal_id = entry.meal_id
        PlannerService(db_session, uid).mark_completed(entry.id)

        SampleDataService(db_session, uid).remove()

        remaining = {r.id for r in db_session.execute(select(Recipe).where(Recipe.user_id == uid)).scalars()}
        assert unfavorited.id in remaining
        assert grouped.id in remaining
        assert db_session.get(Meal, cooked_meal_id) is not None
        assert db_session.get(PlannerEntry, entry.id).is_completed


class TestShoppingResyncOnDelete:
    def test_deleting_a_planned_recipe_removes_its_shopping_items(self, db_session, test_user):
        uid = test_user.id
        SampleDataService(db_session, uid).seed()
        before = _recipe_items(db_session, uid)
        assert before

        for recipe in _sample_recipes(db_session, uid):
            RecipeService(db_session, uid).delete_recipe(recipe.id)

        db_session.expire_all()
        assert _recipe_items(db_session, uid) == []

    def test_deleting_a_planned_meal_removes_its_shopping_items(self, db_session, test_user):
        uid = test_user.id
        SampleDataService(db_session, uid).seed()
        meal_ids = {
            e.meal_id
            for e in db_session.execute(select(PlannerEntry).where(PlannerEntry.user_id == uid)).scalars()
        }
        for meal_id in meal_ids:
            MealService(db_session, uid).delete_meal(meal_id)

        db_session.expire_all()
        assert _recipe_items(db_session, uid) == []


class TestSeededSettingsPersist:
    def test_categories_from_a_get_are_real_rows(self, db_session, test_user):
        categories = UserCategoryService(db_session, test_user.id).get_all_categories()
        assert categories
        db_session.expire_all()
        assert db_session.get(UserCategory, categories[0].id) is not None


class TestPlannerPositions:
    def test_positions_increase_after_position_zero(self, db_session, test_user):
        repo = PlannerEntryRepo(db_session)
        uid = test_user.id
        first = repo._get_next_position(uid)
        assert first == 0
        db_session.add(
            PlannerEntry(
                meal_id=_meal(db_session, uid).id, position=0, user_id=uid
            )
        )
        db_session.flush()
        assert repo._get_next_position(uid) == 1


def _meal(db_session: Session, uid: int) -> Meal:
    recipe = Recipe(recipe_name="R", recipe_category="c", meal_type="Dinner", user_id=uid)
    db_session.add(recipe)
    db_session.flush()
    meal = Meal(meal_name="M", main_recipe_id=recipe.id, user_id=uid)
    db_session.add(meal)
    db_session.flush()
    return meal
