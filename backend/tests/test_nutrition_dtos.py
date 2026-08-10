"""Tests for nutrition-related Pydantic DTOs.

Covers:
- NutritionFactsDTO validation (ge=0 constraints, optional fields)
- NutritionFactsResponseDTO.from_model()
- NutritionEstimationRequestDTO validation
- NutritionEstimationResponseDTO structure
- RecipeCreateDTO / RecipeUpdateDTO with embedded nutrition_facts
"""

import pytest
from pydantic import ValidationError

from app.dtos.nutrition_dtos import (
    NutritionEstimationRequestDTO,
    NutritionEstimationResponseDTO,
    NutritionFactsDTO,
    NutritionFactsResponseDTO,
    NutritionIngredientDTO,
)
from app.dtos.recipe_dtos import RecipeCreateDTO, RecipeUpdateDTO


class TestNutritionFactsDTO:
    """Tests for the NutritionFactsDTO input model."""

    def test_valid_full_data(self, sample_nutrition_data):
        """All fields provided with valid values."""
        dto = NutritionFactsDTO(**sample_nutrition_data)
        assert dto.calories == 350
        assert dto.protein_g == 12.5
        assert dto.is_ai_estimated is False

    def test_all_fields_optional(self):
        """All numeric fields default to None."""
        dto = NutritionFactsDTO()
        assert dto.calories is None
        assert dto.protein_g is None
        assert dto.total_fat_g is None
        assert dto.saturated_fat_g is None
        assert dto.trans_fat_g is None
        assert dto.cholesterol_mg is None
        assert dto.sodium_mg is None
        assert dto.total_carbs_g is None
        assert dto.dietary_fiber_g is None
        assert dto.total_sugars_g is None
        assert dto.is_ai_estimated is False

    def test_negative_calories_rejected(self):
        """Negative calorie value is rejected (ge=0)."""
        with pytest.raises(ValidationError) as exc_info:
            NutritionFactsDTO(calories=-10)
        assert "calories" in str(exc_info.value)

    def test_negative_protein_rejected(self):
        """Negative protein_g value is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(protein_g=-1.0)

    def test_negative_fat_rejected(self):
        """Negative total_fat_g is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(total_fat_g=-0.5)

    def test_negative_sodium_rejected(self):
        """Negative sodium_mg is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(sodium_mg=-100)

    def test_negative_carbs_rejected(self):
        """Negative total_carbs_g is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(total_carbs_g=-5)

    def test_negative_fiber_rejected(self):
        """Negative dietary_fiber_g is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(dietary_fiber_g=-1)

    def test_negative_sugars_rejected(self):
        """Negative total_sugars_g is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(total_sugars_g=-2)

    def test_negative_cholesterol_rejected(self):
        """Negative cholesterol_mg is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(cholesterol_mg=-50)

    def test_negative_saturated_fat_rejected(self):
        """Negative saturated_fat_g is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(saturated_fat_g=-1)

    def test_negative_trans_fat_rejected(self):
        """Negative trans_fat_g is rejected."""
        with pytest.raises(ValidationError):
            NutritionFactsDTO(trans_fat_g=-0.1)

    def test_zero_values_accepted(self):
        """Zero is a valid value for all numeric fields."""
        dto = NutritionFactsDTO(
            calories=0,
            protein_g=0.0,
            total_fat_g=0.0,
            saturated_fat_g=0.0,
            trans_fat_g=0.0,
            cholesterol_mg=0.0,
            sodium_mg=0.0,
            total_carbs_g=0.0,
            dietary_fiber_g=0.0,
            total_sugars_g=0.0,
        )
        assert dto.calories == 0
        assert dto.protein_g == 0.0

    def test_ai_estimated_defaults_false(self):
        """is_ai_estimated defaults to False."""
        dto = NutritionFactsDTO(calories=100)
        assert dto.is_ai_estimated is False

    def test_ai_estimated_can_be_true(self):
        """is_ai_estimated can be set to True."""
        dto = NutritionFactsDTO(calories=100, is_ai_estimated=True)
        assert dto.is_ai_estimated is True

    def test_from_attributes_mode(self):
        """DTO has from_attributes=True for ORM compatibility."""
        assert NutritionFactsDTO.model_config.get("from_attributes") is True


class TestNutritionFactsResponseDTO:
    """Tests for the response DTO (includes id + recipe_id)."""

    def test_includes_id_and_recipe_id(self):
        """Response DTO adds id and recipe_id fields."""
        dto = NutritionFactsResponseDTO(
            id=1,
            recipe_id=10,
            calories=350,
            protein_g=12.0,
        )
        assert dto.id == 1
        assert dto.recipe_id == 10
        assert dto.calories == 350

    def test_from_model(self, db_session, sample_recipe, sample_nutrition_data):
        """from_model() correctly maps a NutritionFacts model to a response DTO."""
        from app.models.nutrition_facts import NutritionFacts

        nf = NutritionFacts(recipe_id=sample_recipe.id, **sample_nutrition_data)
        db_session.add(nf)
        db_session.flush()

        dto = NutritionFactsResponseDTO.from_model(nf)

        assert dto.id == nf.id
        assert dto.recipe_id == sample_recipe.id
        assert dto.calories == 350
        assert dto.protein_g == 12.5
        assert dto.is_ai_estimated is False


class TestNutritionIngredientDTO:
    """Tests for the simplified ingredient DTO used in estimation requests."""

    def test_required_name(self):
        """ingredient_name is required."""
        dto = NutritionIngredientDTO(ingredient_name="Flour")
        assert dto.ingredient_name == "Flour"
        assert dto.quantity is None
        assert dto.unit is None

    def test_with_quantity_and_unit(self):
        """All fields can be provided."""
        dto = NutritionIngredientDTO(
            ingredient_name="Butter",
            quantity=2.0,
            unit="tbsp",
        )
        assert dto.quantity == 2.0
        assert dto.unit == "tbsp"


class TestNutritionEstimationRequestDTO:
    """Tests for the AI estimation request DTO."""

    def test_valid_request(self):
        """A valid estimation request with ingredients."""
        dto = NutritionEstimationRequestDTO(
            recipe_name="Pancakes",
            ingredients=[
                NutritionIngredientDTO(ingredient_name="Flour", quantity=2.0, unit="cups"),
                NutritionIngredientDTO(ingredient_name="Eggs", quantity=2.0),
            ],
            servings=4,
        )
        assert dto.recipe_name == "Pancakes"
        assert len(dto.ingredients) == 2
        assert dto.servings == 4

    def test_servings_optional(self):
        """Servings can be omitted (defaults to None)."""
        dto = NutritionEstimationRequestDTO(
            recipe_name="Toast",
            ingredients=[NutritionIngredientDTO(ingredient_name="Bread")],
        )
        assert dto.servings is None

    def test_servings_must_be_positive(self):
        """Servings must be >= 1."""
        with pytest.raises(ValidationError):
            NutritionEstimationRequestDTO(
                recipe_name="Test",
                ingredients=[NutritionIngredientDTO(ingredient_name="X")],
                servings=0,
            )

    def test_empty_ingredients_allowed(self):
        """Empty ingredients list is valid (service handles gracefully)."""
        dto = NutritionEstimationRequestDTO(
            recipe_name="Mystery",
            ingredients=[],
        )
        assert len(dto.ingredients) == 0


class TestNutritionEstimationResponseDTO:
    """Tests for the AI estimation response DTO."""

    def test_success_response(self):
        """Successful response includes nutrition_facts."""
        dto = NutritionEstimationResponseDTO(
            success=True,
            nutrition_facts=NutritionFactsDTO(calories=200, protein_g=8.0),
        )
        assert dto.success is True
        assert dto.nutrition_facts.calories == 200
        assert dto.error is None

    def test_error_response(self):
        """Error response has success=False and an error message."""
        dto = NutritionEstimationResponseDTO(
            success=False,
            error="API key not configured",
        )
        assert dto.success is False
        assert dto.nutrition_facts is None
        assert "API key" in dto.error


class TestRecipeDTOsWithNutrition:
    """Tests for nutrition_facts field on RecipeCreateDTO and RecipeUpdateDTO."""

    def test_create_dto_with_nutrition(self):
        """RecipeCreateDTO accepts an embedded nutrition_facts object."""
        dto = RecipeCreateDTO(
            recipe_name="Salad",
            recipe_category="Healthy",
            meal_type="Lunch",
            nutrition_facts=NutritionFactsDTO(calories=150, protein_g=5.0),
        )
        assert dto.nutrition_facts is not None
        assert dto.nutrition_facts.calories == 150

    def test_create_dto_without_nutrition(self):
        """RecipeCreateDTO nutrition_facts defaults to None."""
        dto = RecipeCreateDTO(
            recipe_name="Salad",
            recipe_category="Healthy",
        )
        assert dto.nutrition_facts is None

    def test_update_dto_with_nutrition(self):
        """RecipeUpdateDTO accepts an embedded nutrition_facts object."""
        dto = RecipeUpdateDTO(
            nutrition_facts=NutritionFactsDTO(calories=400, is_ai_estimated=True),
        )
        assert dto.nutrition_facts.calories == 400
        assert dto.nutrition_facts.is_ai_estimated is True

    def test_update_dto_nutrition_unset(self):
        """RecipeUpdateDTO without nutrition_facts leaves it unset."""
        dto = RecipeUpdateDTO(recipe_name="Updated Name")
        data = dto.model_dump(exclude_unset=True)
        assert "nutrition_facts" not in data

    def test_difficulty_validation_on_create(self):
        """RecipeCreateDTO rejects invalid difficulty values."""
        with pytest.raises(ValidationError) as exc_info:
            RecipeCreateDTO(
                recipe_name="Test",
                recipe_category="Test",
                difficulty="Super Hard",
            )
        assert "difficulty" in str(exc_info.value)

    def test_difficulty_validation_valid_values(self):
        """RecipeCreateDTO accepts valid difficulty values."""
        for diff in ("Easy", "Medium", "Hard"):
            dto = RecipeCreateDTO(
                recipe_name="Test",
                recipe_category="Test",
                difficulty=diff,
            )
            assert dto.difficulty == diff
