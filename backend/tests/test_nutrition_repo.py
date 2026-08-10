"""Tests for nutrition facts CRUD through RecipeRepo.

Covers:
- Creating a recipe with nutrition_facts via persist_recipe_and_links
- Reading nutrition_facts through get_by_id (joinedload)
- Updating nutrition_facts (modify existing, add new, delete)
- Verifying nutrition data survives recipe update cycles
"""

import pytest

from app.dtos.nutrition_dtos import NutritionFactsDTO
from app.dtos.recipe_dtos import RecipeCreateDTO, RecipeIngredientDTO, RecipeUpdateDTO
from app.models.nutrition_facts import NutritionFacts
from app.repositories.recipe_repo import RecipeRepo


class TestRecipeRepoCreateWithNutrition:
    """Tests for persist_recipe_and_links with nutrition_facts."""

    def test_create_recipe_with_nutrition(self, db_session, test_user, sample_nutrition_data):
        """Creating a recipe with nutrition_facts persists the linked row."""
        repo = RecipeRepo(db_session, user_id=test_user.id)

        dto = RecipeCreateDTO(
            recipe_name="Nutritious Pasta",
            recipe_category="Italian",
            meal_type="Dinner",
            servings=4,
            ingredients=[
                RecipeIngredientDTO(
                    ingredient_name="Pasta",
                    ingredient_category="Grains",
                    quantity=200,
                    unit="g",
                ),
            ],
            nutrition_facts=NutritionFactsDTO(**sample_nutrition_data),
        )

        recipe = repo.persist_recipe_and_links(dto, test_user.id)
        db_session.flush()

        # Re-fetch to confirm persistence
        fetched = repo.get_by_id(recipe.id, test_user.id)
        assert fetched is not None
        assert fetched.nutrition_facts is not None
        assert fetched.nutrition_facts.calories == 350
        assert fetched.nutrition_facts.protein_g == 12.5
        assert fetched.nutrition_facts.is_ai_estimated is False

    def test_create_recipe_without_nutrition(self, db_session, test_user):
        """Creating a recipe without nutrition_facts leaves it as None."""
        repo = RecipeRepo(db_session, user_id=test_user.id)

        dto = RecipeCreateDTO(
            recipe_name="Simple Toast",
            recipe_category="Breakfast",
            ingredients=[],
        )

        recipe = repo.persist_recipe_and_links(dto, test_user.id)
        fetched = repo.get_by_id(recipe.id, test_user.id)

        assert fetched is not None
        assert fetched.nutrition_facts is None

    def test_create_recipe_with_ai_estimated_nutrition(self, db_session, test_user):
        """AI-estimated nutrition correctly sets is_ai_estimated=True."""
        repo = RecipeRepo(db_session, user_id=test_user.id)

        dto = RecipeCreateDTO(
            recipe_name="AI Salad",
            recipe_category="Healthy",
            ingredients=[
                RecipeIngredientDTO(
                    ingredient_name="Lettuce",
                    ingredient_category="Vegetables",
                ),
            ],
            nutrition_facts=NutritionFactsDTO(
                calories=50,
                protein_g=2.0,
                is_ai_estimated=True,
            ),
        )

        recipe = repo.persist_recipe_and_links(dto, test_user.id)
        fetched = repo.get_by_id(recipe.id, test_user.id)

        assert fetched.nutrition_facts.is_ai_estimated is True
        assert fetched.nutrition_facts.calories == 50

    def test_create_recipe_with_partial_nutrition(self, db_session, test_user):
        """Nutrition can have only some fields filled (others null)."""
        repo = RecipeRepo(db_session, user_id=test_user.id)

        dto = RecipeCreateDTO(
            recipe_name="Quick Snack",
            recipe_category="Snacks",
            ingredients=[],
            nutrition_facts=NutritionFactsDTO(calories=100),
        )

        recipe = repo.persist_recipe_and_links(dto, test_user.id)
        fetched = repo.get_by_id(recipe.id, test_user.id)

        assert fetched.nutrition_facts.calories == 100
        assert fetched.nutrition_facts.protein_g is None
        assert fetched.nutrition_facts.total_fat_g is None


class TestRecipeRepoGetWithNutrition:
    """Tests for reading nutrition through get_by_id."""

    def test_get_by_id_eager_loads_nutrition(self, db_session, sample_recipe):
        """get_by_id eager-loads nutrition_facts via joinedload."""
        # Attach nutrition
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=200)
        db_session.add(nf)
        db_session.flush()

        repo = RecipeRepo(db_session, user_id=sample_recipe.user_id)
        fetched = repo.get_by_id(sample_recipe.id, sample_recipe.user_id)

        assert fetched.nutrition_facts is not None
        assert fetched.nutrition_facts.calories == 200

    def test_get_by_id_no_nutrition(self, db_session, sample_recipe):
        """get_by_id returns None for nutrition_facts when none exists."""
        repo = RecipeRepo(db_session, user_id=sample_recipe.user_id)
        fetched = repo.get_by_id(sample_recipe.id, sample_recipe.user_id)

        assert fetched.nutrition_facts is None

    def test_get_by_id_user_isolation(self, db_session, sample_recipe, second_user):
        """A different user cannot see another user's recipe (and its nutrition)."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=300)
        db_session.add(nf)
        db_session.flush()

        repo = RecipeRepo(db_session, user_id=second_user.id)
        fetched = repo.get_by_id(sample_recipe.id, second_user.id)

        assert fetched is None


class TestRecipeRepoUpdateNutrition:
    """Tests for updating nutrition through update_recipe."""

    def test_add_nutrition_to_existing_recipe(self, db_session, sample_recipe, test_user):
        """Adding nutrition_facts to a recipe that had none creates a new row."""
        repo = RecipeRepo(db_session, user_id=test_user.id)

        update_dto = RecipeUpdateDTO(
            nutrition_facts=NutritionFactsDTO(calories=250, protein_g=10.0),
        )
        repo.update_recipe(sample_recipe.id, update_dto, test_user.id)
        db_session.flush()

        # Expire cached state so the relationship is re-loaded from DB
        db_session.expire(sample_recipe)
        fetched = repo.get_by_id(sample_recipe.id, test_user.id)
        assert fetched.nutrition_facts is not None
        assert fetched.nutrition_facts.calories == 250
        assert fetched.nutrition_facts.protein_g == 10.0

    def test_modify_existing_nutrition(self, db_session, sample_recipe, test_user):
        """Updating nutrition_facts on a recipe with existing nutrition modifies in place."""
        # First add nutrition
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=200, protein_g=8.0)
        db_session.add(nf)
        db_session.flush()
        original_nf_id = nf.id

        repo = RecipeRepo(db_session, user_id=test_user.id)

        update_dto = RecipeUpdateDTO(
            nutrition_facts=NutritionFactsDTO(calories=300, protein_g=15.0),
        )
        updated = repo.update_recipe(sample_recipe.id, update_dto, test_user.id)
        db_session.flush()

        # Should update in place, same ID
        assert updated.nutrition_facts.id == original_nf_id
        assert updated.nutrition_facts.calories == 300
        assert updated.nutrition_facts.protein_g == 15.0

    def test_delete_nutrition_by_setting_none(self, db_session, test_user):
        """Setting nutrition_facts=None explicitly deletes the nutrition row."""
        from app.models.recipe import Recipe

        recipe = Recipe(
            recipe_name="Temp Recipe",
            recipe_category="Test",
            meal_type="Dinner",
            user_id=test_user.id,
        )
        db_session.add(recipe)
        db_session.flush()

        nf = NutritionFacts(recipe_id=recipe.id, calories=100)
        db_session.add(nf)
        db_session.flush()
        nf_id = nf.id

        repo = RecipeRepo(db_session, user_id=test_user.id)

        # Explicitly set nutrition_facts to None to trigger deletion
        update_dto = RecipeUpdateDTO(nutrition_facts=None)
        repo.update_recipe(recipe.id, update_dto, test_user.id)
        db_session.flush()

        # Expire cached state so relationship and identity map are refreshed
        db_session.expire_all()

        # The DB row should be deleted
        assert db_session.get(NutritionFacts, nf_id) is None
        # Re-fetch recipe to verify relationship is cleared
        fetched = repo.get_by_id(recipe.id, test_user.id)
        assert fetched.nutrition_facts is None

    def test_update_other_fields_preserves_nutrition(self, db_session, sample_recipe, test_user):
        """Updating recipe fields without touching nutrition_facts preserves it."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=500)
        db_session.add(nf)
        db_session.flush()

        repo = RecipeRepo(db_session, user_id=test_user.id)

        update_dto = RecipeUpdateDTO(recipe_name="Renamed Pasta")
        updated = repo.update_recipe(sample_recipe.id, update_dto, test_user.id)
        db_session.flush()

        assert updated.recipe_name == "Renamed Pasta"
        # Nutrition should be untouched
        assert updated.nutrition_facts is not None
        assert updated.nutrition_facts.calories == 500

    def test_update_nutrition_all_fields(self, db_session, sample_recipe, test_user):
        """All 10 nutrition fields + is_ai_estimated can be updated at once."""
        nf = NutritionFacts(recipe_id=sample_recipe.id, calories=100)
        db_session.add(nf)
        db_session.flush()

        repo = RecipeRepo(db_session, user_id=test_user.id)

        update_dto = RecipeUpdateDTO(
            nutrition_facts=NutritionFactsDTO(
                calories=400,
                protein_g=20.0,
                total_fat_g=15.0,
                saturated_fat_g=5.0,
                trans_fat_g=0.5,
                cholesterol_mg=60.0,
                sodium_mg=800.0,
                total_carbs_g=45.0,
                dietary_fiber_g=6.0,
                total_sugars_g=8.0,
                is_ai_estimated=True,
            ),
        )
        updated = repo.update_recipe(sample_recipe.id, update_dto, test_user.id)
        db_session.flush()

        nf_updated = updated.nutrition_facts
        assert nf_updated.calories == 400
        assert nf_updated.protein_g == 20.0
        assert nf_updated.total_fat_g == 15.0
        assert nf_updated.saturated_fat_g == 5.0
        assert nf_updated.trans_fat_g == 0.5
        assert nf_updated.cholesterol_mg == 60.0
        assert nf_updated.sodium_mg == 800.0
        assert nf_updated.total_carbs_g == 45.0
        assert nf_updated.dietary_fiber_g == 6.0
        assert nf_updated.total_sugars_g == 8.0
        assert nf_updated.is_ai_estimated is True
