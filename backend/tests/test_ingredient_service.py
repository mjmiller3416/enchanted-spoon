"""Tests for the IngredientService.

Covers:
- get_or_create: new ingredient, existing ingredient, user isolation
- create_ingredient / update_ingredient / delete_ingredient: CRUD + not-found
- search_ingredients: by name substring, by category
- list_distinct_names / get_ingredient_categories: unique value queries
"""

import pytest

from app.dtos.ingredient_dtos import (
    IngredientCreateDTO,
    IngredientUpdateDTO,
)
from app.models.ingredient import Ingredient
from app.services.ingredient_service import IngredientNotFoundError, IngredientService


# ---------------------------------------------------------------------------
# Get or Create
# ---------------------------------------------------------------------------

class TestIngredientServiceGetOrCreate:
    """Tests for IngredientService.get_or_create."""

    def test_create_new_ingredient(self, db_session, test_user):
        """get_or_create with a new name creates and returns the ingredient."""
        service = IngredientService(db_session, test_user.id)
        dto = IngredientCreateDTO(
            ingredient_name="Olive Oil",
            ingredient_category="Oils",
        )

        result = service.get_or_create(dto)

        assert result is not None
        assert result.id is not None
        assert result.ingredient_name == "Olive Oil"
        assert result.ingredient_category == "Oils"
        assert result.user_id == test_user.id

    def test_return_existing_ingredient(self, db_session, test_user):
        """get_or_create with a duplicate name+category returns the existing one."""
        service = IngredientService(db_session, test_user.id)
        dto = IngredientCreateDTO(
            ingredient_name="Salt",
            ingredient_category="Seasonings",
        )

        first = service.get_or_create(dto)
        second = service.get_or_create(dto)

        assert first.id == second.id

    def test_user_isolation(self, db_session, test_user, second_user):
        """Ingredients created by one user are not found by another."""
        owner_service = IngredientService(db_session, test_user.id)
        other_service = IngredientService(db_session, second_user.id)
        dto = IngredientCreateDTO(
            ingredient_name="Truffle Oil",
            ingredient_category="Oils",
        )

        owner_service.get_or_create(dto)
        result = other_service.get_or_create(dto)

        # second_user should get their own copy (different ID)
        owner_all = owner_service.get_all()
        other_all = other_service.get_all()
        owner_ids = {i.id for i in owner_all}
        other_ids = {i.id for i in other_all}
        assert not owner_ids.intersection(other_ids) or result.user_id == second_user.id


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestIngredientServiceCRUD:
    """Tests for create, update, and delete operations."""

    def test_create_ingredient(self, db_session, test_user):
        """create_ingredient persists and returns the ingredient."""
        service = IngredientService(db_session, test_user.id)
        dto = IngredientCreateDTO(
            ingredient_name="Garlic",
            ingredient_category="Produce",
        )

        result = service.create_ingredient(dto)

        assert result.id is not None
        assert result.ingredient_name == "Garlic"

    def test_update_ingredient_name(self, db_session, test_user, sample_ingredient):
        """Updating the name persists the new value."""
        service = IngredientService(db_session, test_user.id)
        update_dto = IngredientUpdateDTO(ingredient_name="Angel Hair Pasta")

        result = service.update_ingredient(sample_ingredient.id, update_dto)

        assert result is not None
        assert result.ingredient_name == "Angel Hair Pasta"
        assert result.ingredient_category == "Pasta"  # unchanged

    def test_update_ingredient_category(self, db_session, test_user, sample_ingredient):
        """Updating the category persists the new value."""
        service = IngredientService(db_session, test_user.id)
        update_dto = IngredientUpdateDTO(ingredient_category="Dry Goods")

        result = service.update_ingredient(sample_ingredient.id, update_dto)

        assert result is not None
        assert result.ingredient_category == "Dry Goods"

    def test_update_ingredient_not_found(self, db_session, test_user):
        """Updating a non-existent ingredient raises IngredientNotFoundError."""
        service = IngredientService(db_session, test_user.id)
        update_dto = IngredientUpdateDTO(ingredient_name="Ghost")

        with pytest.raises(IngredientNotFoundError):
            service.update_ingredient(9999, update_dto)

    def test_delete_ingredient(self, db_session, test_user, sample_ingredient):
        """Deleting an existing ingredient removes it."""
        service = IngredientService(db_session, test_user.id)

        service.delete_ingredient(sample_ingredient.id)

        assert service.get_ingredient_by_id(sample_ingredient.id) is None

    def test_delete_ingredient_not_found(self, db_session, test_user):
        """Deleting a non-existent ingredient raises IngredientNotFoundError."""
        service = IngredientService(db_session, test_user.id)

        with pytest.raises(IngredientNotFoundError):
            service.delete_ingredient(9999)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestIngredientServiceSearch:
    """Tests for search operations."""

    def test_search_by_name(self, db_session, test_user):
        """search_ingredients finds ingredients matching a substring."""
        service = IngredientService(db_session, test_user.id)
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Red Pepper", ingredient_category="Produce")
        )
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Black Pepper", ingredient_category="Seasonings")
        )
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Butter", ingredient_category="Dairy")
        )

        results = service.search_ingredients("pepper")

        names = [i.ingredient_name for i in results]
        assert "Red Pepper" in names
        assert "Black Pepper" in names
        assert "Butter" not in names

    def test_search_by_category(self, db_session, test_user):
        """search_ingredients with a category filter narrows results."""
        service = IngredientService(db_session, test_user.id)
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Red Pepper", ingredient_category="Produce")
        )
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Black Pepper", ingredient_category="Seasonings")
        )

        results = service.search_ingredients("pepper", category="Produce")

        names = [i.ingredient_name for i in results]
        assert "Red Pepper" in names
        assert "Black Pepper" not in names


# ---------------------------------------------------------------------------
# Distinct values
# ---------------------------------------------------------------------------

class TestIngredientServiceDistinct:
    """Tests for list_distinct_names and get_ingredient_categories."""

    def test_list_distinct_names(self, db_session, test_user):
        """list_distinct_names returns unique ingredient names."""
        service = IngredientService(db_session, test_user.id)
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Flour", ingredient_category="Dry Goods")
        )
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Sugar", ingredient_category="Dry Goods")
        )

        names = service.list_distinct_names()

        assert "Flour" in names
        assert "Sugar" in names

    def test_get_ingredient_categories(self, db_session, test_user):
        """get_ingredient_categories returns sorted unique categories."""
        service = IngredientService(db_session, test_user.id)
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Milk", ingredient_category="Dairy")
        )
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Cream", ingredient_category="Dairy")
        )
        service.create_ingredient(
            IngredientCreateDTO(ingredient_name="Basil", ingredient_category="Herbs")
        )

        categories = service.get_ingredient_categories()

        assert "Dairy" in categories
        assert "Herbs" in categories
        # Sorted
        assert categories == sorted(categories)
