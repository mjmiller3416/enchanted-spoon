"""Tests for manual shopping item category handling.

Regression coverage for #136/#143: manual items added without an explicit
category used to land in a NULL category (client-side "Other" fallback)
while every other item source used the literal "other" slug, splitting the
shopping list into two visually-identical "Other" groups.
"""

import pytest
from sqlalchemy.orm import Session

from app.dtos.shopping_dtos import ManualItemCreateDTO, ShoppingItemUpdateDTO
from app.models.shopping_item import ShoppingItem
from app.models.user import User
from app.services.shopping import ShoppingService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def service(db_session: Session, test_user: User) -> ShoppingService:
    return ShoppingService(db_session, test_user.id)


def make_dto(**overrides) -> ManualItemCreateDTO:
    data = {"ingredient_name": "Duct Tape", "quantity": 1}
    data.update(overrides)
    return ManualItemCreateDTO(**data)


# ---------------------------------------------------------------------------
# DTO validation
# ---------------------------------------------------------------------------

class TestManualItemCreateDTO:
    def test_no_category_stays_none(self):
        dto = make_dto()
        assert dto.category is None

    def test_category_normalized_to_lowercase(self):
        dto = make_dto(category="  Household ")
        assert dto.category == "household"

    def test_empty_category_normalized_to_none(self):
        dto = make_dto(category="")
        assert dto.category is None


class TestShoppingItemUpdateDTO:
    def test_category_normalized_to_lowercase(self):
        dto = ShoppingItemUpdateDTO(category="  Produce ")
        assert dto.category == "produce"


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

class TestShoppingItemCreateManual:
    def test_missing_category_defaults_to_other(self):
        item = ShoppingItem.create_manual(ingredient_name="Duct Tape", quantity=1)
        assert item.category == "other"

    def test_explicit_category_preserved(self):
        item = ShoppingItem.create_manual(
            ingredient_name="Duct Tape", quantity=1, category="household"
        )
        assert item.category == "household"


# ---------------------------------------------------------------------------
# Service integration
# ---------------------------------------------------------------------------

class TestAddManualItem:
    def test_item_without_category_gets_other(self, service: ShoppingService):
        result = service.add_manual_item(make_dto())
        assert result is not None
        assert result.category == "other"

    def test_two_uncategorized_items_share_one_category(self, service: ShoppingService):
        first = service.add_manual_item(make_dto(ingredient_name="Duct Tape"))
        second = service.add_manual_item(
            make_dto(ingredient_name="Batteries", category="Other")
        )
        assert first is not None and second is not None
        assert first.category == second.category == "other"


class TestAddManualItems:
    """Batch add used by Genie: skips items already needed, revives checked-off ones."""

    def test_new_items_are_added(self, service: ShoppingService):
        result = service.add_manual_items(
            [make_dto(ingredient_name="Milk"), make_dto(ingredient_name="Eggs", quantity=12)]
        )
        assert result is not None
        assert [i.ingredient_name for i in result.added] == ["Milk", "Eggs"]
        assert result.reactivated == [] and result.already_listed == []
        assert len(service.get_shopping_list().items) == 2

    def test_needed_item_is_skipped_case_insensitively(self, service: ShoppingService):
        service.add_manual_item(make_dto(ingredient_name="Milk"))

        result = service.add_manual_items([make_dto(ingredient_name="milk")])

        assert result is not None
        assert result.added == []
        assert result.already_listed == ["Milk"]
        assert len(service.get_shopping_list().items) == 1

    @pytest.mark.parametrize(
        "listed, requested",
        [("Egg", "Eggs"), ("Tomato", "tomatoes"), ("Berry", "Berries"),
         ("Peach", "Peaches"), ("Paper Towel", "paper  towels")],
    )
    def test_plural_matches_singular(self, service: ShoppingService, listed, requested):
        service.add_manual_item(make_dto(ingredient_name=listed))

        result = service.add_manual_items([make_dto(ingredient_name=requested)])

        assert result is not None
        assert result.added == [] and result.already_listed == [listed]

    @pytest.mark.parametrize("listed, requested", [("Hummus", "Humm"), ("Swiss", "Swis")])
    def test_non_plural_endings_are_not_folded(self, service: ShoppingService, listed, requested):
        service.add_manual_item(make_dto(ingredient_name=listed))

        result = service.add_manual_items([make_dto(ingredient_name=requested)])

        assert result is not None
        assert [i.ingredient_name for i in result.added] == [requested]

    def test_checked_off_item_moves_back_to_need(self, service: ShoppingService):
        existing = service.add_manual_item(make_dto(ingredient_name="Milk"))
        service.update_item(existing.id, ShoppingItemUpdateDTO(have=True))

        result = service.add_manual_items([make_dto(ingredient_name="Milk")])

        assert result is not None
        assert result.added == []
        assert [i.id for i in result.reactivated] == [existing.id]
        items = service.get_shopping_list().items
        assert len(items) == 1 and items[0].have is False

    def test_needed_row_wins_over_checked_off_duplicate(self, service: ShoppingService):
        checked = service.add_manual_item(make_dto(ingredient_name="Milk"))
        service.update_item(checked.id, ShoppingItemUpdateDTO(have=True))
        service.add_manual_item(make_dto(ingredient_name="Milk"))

        result = service.add_manual_items([make_dto(ingredient_name="Milk")])

        assert result is not None
        assert result.already_listed == ["Milk"]
        assert result.reactivated == []
