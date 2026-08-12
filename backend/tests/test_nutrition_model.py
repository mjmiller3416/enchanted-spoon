"""Tests for the NutritionFacts SQLAlchemy model.

Covers:
- Creating nutrition facts linked to a recipe
- One-to-one relationship (recipe ↔ nutrition_facts)
- Cascade delete when recipe is deleted
- Field nullability and defaults
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.nutrition_facts import NutritionFacts
from app.models.recipe import Recipe


class TestNutritionFactsModel:
    """Tests for the NutritionFacts ORM model."""

    def test_create_nutrition_facts(self, db_session, sample_recipe, sample_nutrition_data):
        """Creating NutritionFacts with valid data persists correctly."""
        nf = NutritionFacts(
            recipe_id=sample_recipe.id,
            **sample_nutrition_data,
        )
        db_session.add(nf)
        db_session.flush()

        assert nf.id is not None
        assert nf.recipe_id == sample_recipe.id
        assert nf.calories == 350
        assert nf.protein_g == 12.5
        assert nf.total_fat_g == 8.0
        assert nf.saturated_fat_g == 2.5
        assert nf.trans_fat_g == 0.0
        assert nf.cholesterol_mg == 25.0
        assert nf.sodium_mg == 480.0
        assert nf.total_carbs_g == 55.0
        assert nf.dietary_fiber_g == 3.0
        assert nf.total_sugars_g == 4.5
        assert nf.is_ai_estimated is False

    def test_create_nutrition_facts_with_nulls(self, db_session, sample_recipe):
        """All numeric fields are nullable — only recipe_id is required."""
        nf = NutritionFacts(recipe_id=sample_recipe.id)
        db_session.add(nf)
        db_session.flush()

        assert nf.id is not None
        assert nf.calories is None
        assert nf.protein_g is None
        assert nf.total_fat_g is None
        assert nf.is_ai_estimated is False  # default

    def test_is_ai_estimated_default(self, db_session, sample_recipe):
        """is_ai_estimated defaults to False."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=200)
        db_session.add(nf)
        db_session.flush()

        assert nf.is_ai_estimated is False

    def test_is_ai_estimated_true(self, db_session, sample_recipe):
        """is_ai_estimated can be set to True."""
        nf = NutritionFacts(
            recipe_id=sample_recipe.id,
            calories=200,
            is_ai_estimated=True,
        )
        db_session.add(nf)
        db_session.flush()

        assert nf.is_ai_estimated is True

    def test_recipe_relationship(self, db_session, sample_recipe):
        """NutritionFacts.recipe back-populates to the parent Recipe."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=100)
        db_session.add(nf)
        db_session.flush()

        assert nf.recipe.id == sample_recipe.id
        assert nf.recipe.recipe_name == "Test Pasta"

    def test_recipe_nutrition_facts_relationship(self, db_session, sample_recipe):
        """Recipe.nutrition_facts gives access to the linked NutritionFacts."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=100)
        db_session.add(nf)
        db_session.flush()

        # Refresh to pick up relationship
        db_session.refresh(sample_recipe)

        assert sample_recipe.nutrition_facts is not None
        assert sample_recipe.nutrition_facts.calories == 100

    def test_one_to_one_unique_constraint(self, db_session, sample_recipe):
        """Only one NutritionFacts row per recipe (unique constraint on recipe_id)."""
        nf1 = NutritionFacts(recipe_id=sample_recipe.id, calories=100)
        db_session.add(nf1)
        db_session.flush()

        nf2 = NutritionFacts(recipe_id=sample_recipe.id, calories=200)
        db_session.add(nf2)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_cascade_delete_with_recipe(self, db_session, test_user):
        """Deleting a recipe cascades to delete its NutritionFacts."""
        recipe = Recipe(
            recipe_name="Deletable Recipe",
            recipe_category="Test",
            meal_type="Dinner",
            user_id=test_user.id,
        )
        db_session.add(recipe)
        db_session.flush()

        nf = NutritionFacts(recipe_id=recipe.id, calories=500)
        db_session.add(nf)
        db_session.flush()

        nf_id = nf.id
        db_session.delete(recipe)
        db_session.flush()

        # NutritionFacts row should be gone
        result = db_session.get(NutritionFacts, nf_id)
        assert result is None

    def test_foreign_key_requires_valid_recipe(self, db_session):
        """NutritionFacts with a non-existent recipe_id raises IntegrityError."""
        nf = NutritionFacts(recipe_id=99999, calories=100)
        db_session.add(nf)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_repr(self, db_session, sample_recipe):
        """__repr__ includes id, recipe_id, and calories."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=250)
        db_session.add(nf)
        db_session.flush()

        repr_str = repr(nf)
        assert "NutritionFacts" in repr_str
        assert str(nf.id) in repr_str
        assert str(sample_recipe.id) in repr_str
        assert "250" in repr_str
