"""Tests for the Hearth wall-display shopping-list integration.

Covers the contract DTOs and mappers (pure), the ingredient-library category
lookup, the ``add_named_item`` service path, and the two routes
(``GET /api/hearth/shopping``, ``POST /api/hearth/shopping/items``) end to end
over a file-backed DB. Auth for these endpoints is the shared
``get_integration_user`` dependency, already covered by
``test_shopping_external_ingest``; here it is overridden to the seeded user.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.auth import get_integration_user
from app.api.hearth import router
from app.database.db import get_session
from app.dtos.hearth_dtos import (
    HearthAddShoppingItemDTO,
    add_result_from_batch,
    shopping_item_from_response,
)
from app.dtos.shopping_dtos import (
    ExternalItemUpsertDTO,
    ManualItemCreateDTO,
    ManualItemsAddResultDTO,
    ShoppingItemResponseDTO,
)
from app.models.ingredient import Ingredient
from app.models.shopping_item import ShoppingItem
from app.models.user import User
from app.repositories.ingredient_repo import IngredientRepo
from app.services.shopping import ShoppingService


def _response_item(**overrides) -> ShoppingItemResponseDTO:
    data = dict(
        id=3,
        ingredient_name="Milk",
        quantity=1.0,
        unit=None,
        category="dairy",
        source="manual",
        have=False,
    )
    data.update(overrides)
    return ShoppingItemResponseDTO(**data)


def _add_ingredient(session: Session, user_id: int, name: str, category: str) -> None:
    session.add(Ingredient(ingredient_name=name, ingredient_category=category, user_id=user_id))
    session.flush()


# ---------------------------------------------------------------------------
# Request DTO
# ---------------------------------------------------------------------------

class TestHearthAddShoppingItemDTO:
    def test_name_is_stripped(self):
        assert HearthAddShoppingItemDTO(name="  Milk  ").name == "Milk"

    @pytest.mark.parametrize("name", ["", "   "])
    def test_blank_name_rejected(self, name):
        with pytest.raises(ValidationError):
            HearthAddShoppingItemDTO(name=name)

    def test_overlong_name_rejected(self):
        with pytest.raises(ValidationError):
            HearthAddShoppingItemDTO(name="x" * 256)

    def test_category_optional_and_normalized(self):
        assert HearthAddShoppingItemDTO(name="Milk").category is None
        assert HearthAddShoppingItemDTO(name="Milk", category=" Dairy ").category == "dairy"
        assert HearthAddShoppingItemDTO(name="Milk", category="  ").category is None


# ---------------------------------------------------------------------------
# Pure mappers
# ---------------------------------------------------------------------------

class TestShoppingItemFromResponse:
    def test_maps_row_fields(self):
        row = shopping_item_from_response(
            _response_item(quantity=2.5, unit="lb", source="recipe", have=True)
        )
        assert row.id == 3
        assert row.name == "Milk"
        assert row.quantity == 2.5
        assert row.unit == "lb"
        assert row.category == "dairy"
        assert row.source == "recipe"
        assert row.have is True


class TestAddResultFromBatch:
    def test_added(self):
        result = add_result_from_batch(
            ManualItemsAddResultDTO(added=[_response_item()]), "milk"
        )
        assert (result.status, result.name) == ("added", "Milk")

    def test_reactivated_reports_existing_spelling(self):
        result = add_result_from_batch(
            ManualItemsAddResultDTO(reactivated=[_response_item(ingredient_name="Whole Milk")]),
            "whole milk",
        )
        assert (result.status, result.name) == ("reactivated", "Whole Milk")

    def test_already_listed(self):
        result = add_result_from_batch(
            ManualItemsAddResultDTO(already_listed=["Milk"]), "milk"
        )
        assert (result.status, result.name) == ("already_listed", "Milk")


# ---------------------------------------------------------------------------
# Ingredient-library category lookup
# ---------------------------------------------------------------------------

class TestFindCategoryByNames:
    def test_exact_match_is_case_insensitive(self, db_session: Session, test_user: User):
        _add_ingredient(db_session, test_user.id, "Milk", "dairy")
        repo = IngredientRepo(db_session, test_user.id)
        assert repo.find_category_by_names(["MILK"]) == "dairy"

    def test_no_match_returns_none(self, db_session: Session, test_user: User):
        _add_ingredient(db_session, test_user.id, "Milk", "dairy")
        repo = IngredientRepo(db_session, test_user.id)
        assert repo.find_category_by_names(["Milkshake"]) is None
        assert repo.find_category_by_names([]) is None

    def test_wildcard_characters_match_literally(self, db_session: Session, test_user: User):
        _add_ingredient(db_session, test_user.id, "Milk", "dairy")
        repo = IngredientRepo(db_session, test_user.id)
        assert repo.find_category_by_names(["M_lk"]) is None
        assert repo.find_category_by_names(["%"]) is None

    def test_specific_category_beats_other(self, db_session: Session, test_user: User):
        _add_ingredient(db_session, test_user.id, "Lemon", "other")
        _add_ingredient(db_session, test_user.id, "Lemon", "produce")
        repo = IngredientRepo(db_session, test_user.id)
        assert repo.find_category_by_names(["lemon"]) == "produce"

    def test_scoped_to_user(self, db_session: Session, test_user: User, second_user: User):
        _add_ingredient(db_session, second_user.id, "Milk", "dairy")
        repo = IngredientRepo(db_session, test_user.id)
        assert repo.find_category_by_names(["Milk"]) is None


# ---------------------------------------------------------------------------
# Service: add_named_item
# ---------------------------------------------------------------------------

def _named(name: str, category=None) -> ManualItemCreateDTO:
    return ManualItemCreateDTO(ingredient_name=name, quantity=1, category=category)


class TestAddNamedItem:
    def test_new_item_takes_category_from_ingredient_library(
        self, db_session: Session, test_user: User
    ):
        _add_ingredient(db_session, test_user.id, "Milk", "Dairy")
        result = ShoppingService(db_session, test_user.id).add_named_item(_named("milk"))
        assert result is not None
        assert len(result.added) == 1
        assert result.added[0].category == "dairy"
        assert result.added[0].source == "manual"
        assert result.added[0].quantity == 1

    def test_plural_finds_singular_ingredient(self, db_session: Session, test_user: User):
        _add_ingredient(db_session, test_user.id, "Egg", "dairy")
        result = ShoppingService(db_session, test_user.id).add_named_item(_named("Eggs"))
        assert result.added[0].category == "dairy"
        assert result.added[0].ingredient_name == "Eggs"

    def test_unknown_item_files_under_other(self, db_session: Session, test_user: User):
        result = ShoppingService(db_session, test_user.id).add_named_item(_named("Batteries"))
        assert result.added[0].category == "other"

    def test_explicit_category_wins(self, db_session: Session, test_user: User):
        _add_ingredient(db_session, test_user.id, "Milk", "dairy")
        result = ShoppingService(db_session, test_user.id).add_named_item(
            _named("Milk", category="beverages")
        )
        assert result.added[0].category == "beverages"

    def test_needed_item_is_not_duplicated(self, db_session: Session, test_user: User):
        service = ShoppingService(db_session, test_user.id)
        service.add_named_item(_named("Milk"))
        result = service.add_named_item(_named("milk"))
        assert result.added == []
        assert result.already_listed == ["Milk"]
        count = (
            db_session.query(ShoppingItem)
            .filter(ShoppingItem.user_id == test_user.id)
            .count()
        )
        assert count == 1


# ---------------------------------------------------------------------------
# Routes, end to end
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(file_db):
    """A TestClient on the Hearth router, authenticated as seeded user 1."""
    app = FastAPI()
    app.include_router(router, prefix="/api/hearth")

    def _session():
        with file_db() as session:
            yield session

    def _user():
        with file_db() as session:
            return session.get(User, 1)

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_integration_user] = _user
    return TestClient(app)


class TestShoppingRoutes:
    def test_empty_list(self, client: TestClient):
        res = client.get("/api/hearth/shopping")
        assert res.status_code == 200
        assert res.json() == {"items": []}

    def test_add_then_read(self, client: TestClient, file_db):
        with file_db() as session:
            session.add(Ingredient(ingredient_name="Milk", ingredient_category="dairy", user_id=1))
            session.commit()

        res = client.post("/api/hearth/shopping/items", json={"name": "  milk "})
        assert res.status_code == 201
        assert res.json() == {"status": "added", "name": "milk"}

        items = client.get("/api/hearth/shopping").json()["items"]
        assert len(items) == 1
        row = items[0]
        assert row["name"] == "milk"
        assert row["category"] == "dairy"
        assert row["have"] is False
        assert row["source"] == "manual"
        assert row["quantity"] == 1

    def test_repeat_add_reports_already_listed(self, client: TestClient):
        client.post("/api/hearth/shopping/items", json={"name": "Bread"})
        res = client.post("/api/hearth/shopping/items", json={"name": "bread"})
        assert res.status_code == 200
        assert res.json() == {"status": "already_listed", "name": "Bread"}
        assert len(client.get("/api/hearth/shopping").json()["items"]) == 1

    def test_checked_off_item_moves_back_to_need(self, client: TestClient, file_db):
        client.post("/api/hearth/shopping/items", json={"name": "Coffee"})
        with file_db() as session:
            item = session.query(ShoppingItem).filter_by(user_id=1).one()
            item.have = True
            session.commit()

        res = client.post("/api/hearth/shopping/items", json={"name": "coffee"})
        assert res.status_code == 200
        assert res.json() == {"status": "reactivated", "name": "Coffee"}
        items = client.get("/api/hearth/shopping").json()["items"]
        assert [i["have"] for i in items] == [False]

    def test_blank_name_rejected(self, client: TestClient):
        res = client.post("/api/hearth/shopping/items", json={"name": "   "})
        assert res.status_code == 422

    def test_read_shows_every_source(self, client: TestClient, file_db):
        with file_db() as session:
            ShoppingService(session, 1).upsert_external_item(
                ExternalItemUpsertDTO(name="Paper Towels", source="tada", category="household")
            )

        items = client.get("/api/hearth/shopping").json()["items"]
        assert [(i["name"], i["source"]) for i in items] == [("Paper Towels", "tada")]
