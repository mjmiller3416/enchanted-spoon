"""Shopping list quantities only add when the units allow it.

Different recipes that share an ingredient used to collapse onto one line
keyed by a coarse dimension. "2 onions" and "1 lb onions" became "3 onions"
or "3 lb onions", and "2 cloves" plus "1 can" became "3". These tests pin
the sync that builds the list.
"""

from collections import defaultdict

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dtos.shopping_dtos import ManualItemCreateDTO, ShoppingItemUpdateDTO
from app.models.ingredient import Ingredient
from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.user import User
from app.services.shopping import ShoppingService


def _plan(db: Session, user: User, recipes: list[tuple[str, list[tuple]]]) -> None:
    """Put each recipe on the planner. A line is (name, quantity, unit)."""
    ingredients: dict[tuple[str, str], Ingredient] = {}
    for position, (recipe_name, lines) in enumerate(recipes):
        recipe = Recipe(
            recipe_name=recipe_name,
            recipe_category="mains",
            meal_type="dinner",
            user_id=user.id,
        )
        db.add(recipe)
        db.flush()
        for name, quantity, unit in lines:
            key = (name.lower(), "produce")
            ingredient = ingredients.get(key)
            if ingredient is None:
                ingredient = db.scalars(
                    select(Ingredient).where(
                        Ingredient.user_id == user.id,
                        Ingredient.ingredient_name == name,
                        Ingredient.ingredient_category == "produce",
                    )
                ).unique().one_or_none()
            if ingredient is None:
                ingredient = Ingredient(
                    ingredient_name=name,
                    ingredient_category="produce",
                    user_id=user.id,
                )
                db.add(ingredient)
                db.flush()
            ingredients[key] = ingredient
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=quantity,
                    unit=unit,
                )
            )
        meal = Meal(
            meal_name=recipe_name,
            main_recipe_id=recipe.id,
            user_id=user.id,
            is_saved=True,
        )
        db.add(meal)
        db.flush()
        db.add(PlannerEntry(meal_id=meal.id, user_id=user.id, position=position))
    db.flush()


def _lines(db: Session, user: User) -> dict[str, list[tuple]]:
    ShoppingService(db, user.id).sync_shopping_list()
    db.expire_all()
    grouped: dict[str, list[tuple]] = defaultdict(list)
    service = ShoppingService(db, user.id)
    for item in service.get_shopping_list().items:
        if item.source != "recipe":
            continue
        grouped[item.ingredient_name.lower()].append((item.quantity, item.unit or ""))
    return grouped


def _amounts(db: Session, user: User, name: str) -> list[tuple]:
    return sorted(_lines(db, user)[name.lower()])


class TestSameUnitAndConvertibleSums:
    def test_same_unit_quantities_add(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("Chili", [("Onions", 2, "lbs")]),
                ("Soup", [("Onions", 1, "lbs")]),
            ],
        )
        assert _amounts(db_session, test_user, "onions") == [(3, "lb")]

    def test_convertible_mass_uses_a_sensible_unit(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("Tacos", [("Onions", 8, "oz")]),
                ("Stew", [("Onions", 1, "lb")]),
            ],
        )
        assert _amounts(db_session, test_user, "onions") == [(1.5, "lb")]

    def test_plurals_and_abbreviations_share_a_unit(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Onions", 2, "lbs")]),
                ("B", [("Onions", 1, "lb.")]),
                ("C", [("Onions", 1, "pound")]),
                ("D", [("Onions", 1, "pound(s)")]),
                ("E", [("Butter", 1, "tbsp")]),
                ("F", [("Butter", 1, "T")]),
                ("G", [("Butter", 1, "tablespoon")]),
            ],
        )
        lines = _lines(db_session, test_user)
        assert sorted(lines["onions"]) == [(5, "lb")]
        assert sorted(lines["butter"]) == [(3, "tbsp")]

    def test_fractions_and_decimals_add(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Milk", 0.5, "cup"), ("Cheese", 1.5, "oz")]),
                ("B", [("Milk", 0.25, "cup"), ("Cheese", 2.5, "oz")]),
            ],
        )
        lines = _lines(db_session, test_user)
        assert lines["milk"] == [(0.75, "cup")]
        assert lines["cheese"] == [(4, "oz")]


class TestIncompatibleUnitsStaySeparate:
    def test_count_and_mass_are_different_lines(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("Salad", [("Onions", 2, None)]),
                ("Stew", [("Onions", 1, "lb")]),
            ],
        )
        assert _amounts(db_session, test_user, "onions") == [(1, "lb"), (2, "")]

    def test_count_synonyms_still_add(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Onions", 2, "whole")]),
                ("B", [("Onions", 1, "each")]),
            ],
        )
        assert _amounts(db_session, test_user, "onions") == [(3, "")]

    def test_whole_onions_keep_their_unit_when_every_line_uses_it(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Onions", 1, "whole")]),
                ("B", [("Onions", 2, "wholes")]),
            ],
        )
        assert _amounts(db_session, test_user, "onions") == [(3, "whole")]

    def test_mass_and_volume_are_different_lines(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Butter", 1, "lb")]),
                ("B", [("Butter", 1, "cup")]),
            ],
        )
        assert _amounts(db_session, test_user, "butter") == [(1, "cup"), (1, "lb")]

    def test_unknown_units_do_not_add_across_kinds(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Garlic", 2, "cloves"), ("Tomatoes", 2, "can")]),
                ("B", [("Garlic", 1, "can"), ("Tomatoes", 1, "pinch")]),
            ],
        )
        lines = _lines(db_session, test_user)
        assert sorted(lines["garlic"]) == [(1, "can"), (2, "clove")]
        assert sorted(lines["tomatoes"]) == [(1, "pinch"), (2, "can")]

    def test_the_same_unknown_unit_still_adds(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Garlic", 2, "cloves")]),
                ("B", [("Garlic", 1, "clove")]),
            ],
        )
        assert _amounts(db_session, test_user, "garlic") == [(3, "clove")]

    def test_volume_abbreviations_convert(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Stock", 1, "cup")]),
                ("B", [("Stock", 8, "fl oz")]),
            ],
        )
        # 1 cup is 8 fl oz, so the combined amount is 2 cups.
        assert _amounts(db_session, test_user, "stock") == [(2, "cup")]


class TestQuantitylessLines:
    def test_to_taste_does_not_become_zero_or_merge_into_a_measure(self, db_session, test_user):
        _plan(
            db_session,
            test_user,
            [
                ("A", [("Salt", None, "to-taste")]),
                ("B", [("Salt", 1, "tsp"), ("Pepper", 0, None)]),
            ],
        )
        lines = _lines(db_session, test_user)
        assert sorted(lines["salt"]) == [(0, "to taste"), (1, "tsp")]
        assert lines["pepper"] == [(0, "")]


class TestCheckoffAndManualItems:
    def test_checking_one_line_leaves_the_other_and_survives_resync(
        self, db_session, test_user
    ):
        _plan(
            db_session,
            test_user,
            [
                ("Salad", [("Onions", 2, None)]),
                ("Stew", [("Onions", 1, "lb")]),
            ],
        )
        service = ShoppingService(db_session, test_user.id)
        service.sync_shopping_list()
        items = [
            item
            for item in service.get_shopping_list().items
            if item.ingredient_name.lower() == "onions"
        ]
        assert len(items) == 2
        mass = next(item for item in items if item.unit == "lb")
        count = next(item for item in items if not item.unit)
        service.update_item(mass.id, ShoppingItemUpdateDTO(have=True))

        service.sync_shopping_list()
        again = {
            item.id: item
            for item in service.get_shopping_list().items
            if item.ingredient_name.lower() == "onions"
        }
        assert again[mass.id].have is True
        assert again[count.id].have is False
        assert len(again) == 2

    def test_a_larger_total_clears_the_check_and_manual_items_stay(
        self, db_session, test_user
    ):
        _plan(
            db_session,
            test_user,
            [("Stew", [("Onions", 1, "lb")])],
        )
        service = ShoppingService(db_session, test_user.id)
        manual = service.add_manual_item(
            ManualItemCreateDTO(ingredient_name="Paper Towels", quantity=2, unit="roll")
        )
        service.sync_shopping_list()
        onion = next(
            item
            for item in service.get_shopping_list().items
            if item.ingredient_name.lower() == "onions"
        )
        service.update_item(onion.id, ShoppingItemUpdateDTO(have=True))

        _plan(
            db_session,
            test_user,
            [("Chili", [("Onions", 1, "lbs")])],
        )
        service.sync_shopping_list()
        items = service.get_shopping_list().items
        onions = [item for item in items if item.ingredient_name.lower() == "onions"]
        towels = [item for item in items if item.id == manual.id]
        assert len(onions) == 1
        assert onions[0].quantity == pytest.approx(2)
        assert onions[0].unit == "lb"
        assert onions[0].have is False
        assert len(towels) == 1
        assert towels[0].source == "manual"
        assert towels[0].quantity == 2
        assert towels[0].unit == "roll"
        assert towels[0].have is False
