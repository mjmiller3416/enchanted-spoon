"""Tests for the RecipeGenerationService.

Covers:
- Successful recipe generation with mocked Gemini response
- Prompt building with various preference combinations
- JSON parsing of valid / partial / malformed responses
- Nutrition included when estimate_nutrition=True
- Image generation integration (mocked)
- Error handling (API failure, parse failure, import error)
- safe_int / safe_float helper functions (from parse_utils)
- parse_recipe_dict shared parser
- Dynamic category interpolation
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.dtos.recipe_generation_dtos import (
    RecipeGenerationPreferencesDTO,
    RecipeGenerationRequestDTO,
)
from app.services.ai.parse_utils import (
    parse_nutrition_dict,
    parse_recipe_dict,
    safe_float,
    safe_int,
)
from app.services.ai.recipe_generation.service import (
    RecipeGenerationError,
    RecipeGenerationService,
    RecipeParseError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INGREDIENT = {"ingredient_name": "Salt", "ingredient_category": "pantry"}


def _make_gemini_response(text: str):
    """Create a mock Gemini API response containing the given text."""
    part = MagicMock()
    part.text = text

    content = MagicMock()
    content.parts = [part]

    candidate = MagicMock()
    candidate.content = content

    response = MagicMock()
    response.candidates = [candidate]
    return response


def _full_recipe_json(**overrides) -> str:
    """Return a realistic JSON recipe response, with optional field overrides."""
    data = {
        "recipe_name": "Spicy Thai Green Curry",
        "description": "A fragrant and spicy Thai green curry with vegetables.",
        "recipe_category": "vegetarian",
        "meal_type": "dinner",
        "diet_pref": "vegetarian",
        "prep_time": 15,
        "cook_time": 25,
        "difficulty": "Medium",
        "servings": 4,
        "ingredients": [
            {
                "ingredient_name": "Coconut Milk",
                "ingredient_category": "pantry",
                "quantity": 1.0,
                "unit": "can",
            },
            {
                "ingredient_name": "Green Curry Paste",
                "ingredient_category": "condiments",
                "quantity": 3.0,
                "unit": "tbs",
            },
        ],
        "directions": "Heat oil in a wok.\nAdd curry paste and stir.\nPour in coconut milk and simmer.",
        "notes": "Serve over jasmine rice.",
    }
    data.update(overrides)
    return json.dumps(data)


def _full_recipe_with_nutrition_json() -> str:
    """Return a recipe response that includes nutrition_facts."""
    data = json.loads(_full_recipe_json())
    data["nutrition_facts"] = {
        "calories": 450,
        "protein_g": 12.5,
        "total_fat_g": 28.0,
        "saturated_fat_g": 18.5,
        "trans_fat_g": 0.0,
        "cholesterol_mg": 0.0,
        "sodium_mg": 680.0,
        "total_carbs_g": 35.0,
        "dietary_fiber_g": 4.0,
        "total_sugars_g": 6.5,
    }
    return json.dumps(data)


def _make_request(
    prompt: str = "A spicy Thai green curry for 4",
    preferences: dict | None = None,
    generate_image: bool = False,
    estimate_nutrition: bool = True,
    allowed_categories: list[str] | None = None,
) -> RecipeGenerationRequestDTO:
    """Create a standard recipe generation request for testing."""
    prefs = RecipeGenerationPreferencesDTO(**preferences) if preferences else None
    return RecipeGenerationRequestDTO(
        prompt=prompt,
        preferences=prefs,
        generate_image=generate_image,
        estimate_nutrition=estimate_nutrition,
        allowed_categories=allowed_categories or [],
    )


# ---------------------------------------------------------------------------
# Fixture: patched service (bypasses Gemini client init)
# ---------------------------------------------------------------------------

@pytest.fixture()
def recipe_service():
    """Create a RecipeGenerationService with the Gemini client mocked out."""
    with patch(
        "app.services.ai.recipe_generation.service.get_gemini_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        service = RecipeGenerationService()
        yield service, mock_client


# ---------------------------------------------------------------------------
# Tests — generate() success paths
# ---------------------------------------------------------------------------

class TestRecipeGenerationSuccess:
    """Tests for successful recipe generation."""

    def test_successful_generation(self, recipe_service):
        """Valid Gemini response is parsed into RecipeGenerationResponseDTO."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_json()
        )

        result = service.generate(_make_request())

        assert result.success is True
        assert result.error is None
        assert result.recipe is not None
        assert result.recipe.recipe_name == "Spicy Thai Green Curry"
        assert result.recipe.description == "A fragrant and spicy Thai green curry with vegetables."
        assert result.recipe.recipe_category == "vegetarian"
        assert result.recipe.meal_type == "dinner"
        assert result.recipe.diet_pref == "vegetarian"
        assert result.recipe.prep_time == 15
        assert result.recipe.cook_time == 25
        assert result.recipe.difficulty == "Medium"
        assert result.recipe.servings == 4
        assert len(result.recipe.ingredients) == 2
        assert result.recipe.ingredients[0].ingredient_name == "Coconut Milk"
        assert result.recipe.directions is not None
        assert "Heat oil" in result.recipe.directions
        assert result.recipe.notes == "Serve over jasmine rice."

    def test_nutrition_included_when_requested(self, recipe_service):
        """Nutrition facts are parsed when estimate_nutrition=True."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_with_nutrition_json()
        )

        result = service.generate(_make_request(estimate_nutrition=True))

        assert result.success is True
        assert result.nutrition_facts is not None
        assert result.nutrition_facts.calories == 450
        assert result.nutrition_facts.protein_g == 12.5
        assert result.nutrition_facts.total_fat_g == 28.0
        assert result.nutrition_facts.is_ai_estimated is True

    def test_nutrition_excluded_when_not_requested(self, recipe_service):
        """Nutrition facts are None when estimate_nutrition=False."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_with_nutrition_json()
        )

        result = service.generate(_make_request(estimate_nutrition=False))

        assert result.success is True
        assert result.nutrition_facts is None

    def test_partial_recipe_fields(self, recipe_service):
        """Missing optional fields get defaults or None."""
        service, mock_client = recipe_service

        minimal_json = json.dumps({
            "recipe_name": "Simple Toast",
            "ingredients": [
                {"ingredient_name": "Bread", "ingredient_category": "bakery", "quantity": 2.0, "unit": "slice"},
            ],
            "directions": "Toast the bread.",
        })
        mock_client.models.generate_content.return_value = _make_gemini_response(
            minimal_json
        )

        result = service.generate(_make_request(prompt="Toast"))

        assert result.success is True
        assert result.recipe.recipe_name == "Simple Toast"
        assert result.recipe.recipe_category == "other"  # default
        assert result.recipe.meal_type == "dinner"  # default
        assert result.recipe.description is None
        assert result.recipe.prep_time is None
        assert result.recipe.difficulty is None

    def test_empty_ingredients_list_raises_parse_error(self, recipe_service):
        """Recipe with empty ingredients list raises RecipeParseError, not a hollow success."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_json(ingredients=[])
        )

        with pytest.raises(RecipeParseError, match="ingredients"):
            service.generate(_make_request())

    def test_no_images_by_default(self, recipe_service):
        """Images are None when generate_image=False."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_json()
        )

        result = service.generate(_make_request(generate_image=False))

        assert result.success is True
        assert result.reference_image_data is None
        assert result.banner_image_data is None

    def test_allowed_categories_in_prompt(self, recipe_service):
        """Custom allowed_categories are interpolated into the prompt."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_json()
        )

        result = service.generate(_make_request(
            allowed_categories=["italian", "mexican", "thai"]
        ))

        assert result.success is True
        # Check the prompt sent to Gemini contains our categories
        call_args = mock_client.models.generate_content.call_args
        prompt_text = call_args[1]["contents"][0]["parts"][0]["text"]
        assert "italian|mexican|thai" in prompt_text


# ---------------------------------------------------------------------------
# Tests — image generation
# ---------------------------------------------------------------------------

class TestRecipeImageGeneration:
    """Tests for image generation integration."""

    @patch("app.services.ai.recipe_generation.service.RecipeGenerationService._generate_images")
    def test_images_generated_when_requested(self, mock_gen_images, recipe_service):
        """Image data is included when generate_image=True."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_json()
        )
        mock_gen_images.return_value = ("ref_base64_data", "banner_base64_data")

        result = service.generate(_make_request(generate_image=True))

        assert result.success is True
        assert result.reference_image_data == "ref_base64_data"
        assert result.banner_image_data == "banner_base64_data"
        mock_gen_images.assert_called_once_with("Spicy Thai Green Curry")

    @patch("app.services.ai.recipe_generation.service.RecipeGenerationService._generate_images")
    def test_image_failure_is_nonfatal(self, mock_gen_images, recipe_service):
        """Image generation failure returns None images but recipe still succeeds."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            _full_recipe_json()
        )
        mock_gen_images.return_value = (None, None)

        result = service.generate(_make_request(generate_image=True))

        assert result.success is True
        assert result.recipe is not None
        assert result.reference_image_data is None
        assert result.banner_image_data is None


# ---------------------------------------------------------------------------
# Tests — preferences / prompt building
# ---------------------------------------------------------------------------

class TestPreferencesBuilding:
    """Tests for _build_preferences_text."""

    def test_no_preferences(self):
        """No preferences returns empty string."""
        request = _make_request(preferences=None)
        result = RecipeGenerationService._build_preferences_text(request)
        assert result == ""

    def test_empty_preferences(self):
        """All-None preferences returns empty string."""
        request = _make_request(preferences={})
        result = RecipeGenerationService._build_preferences_text(request)
        assert result == ""

    def test_single_preference(self):
        """Single preference is formatted correctly."""
        request = _make_request(preferences={"category": "thai"})
        result = RecipeGenerationService._build_preferences_text(request)
        assert "Category: thai" in result
        assert "Preferences:" in result

    def test_all_preferences(self):
        """All preferences are included in the output."""
        request = _make_request(preferences={
            "category": "italian",
            "dietary": "Vegetarian",
            "difficulty": "Easy",
            "servings": 6,
            "meal_type": "Lunch",
        })
        result = RecipeGenerationService._build_preferences_text(request)
        assert "Category: italian" in result
        assert "Dietary preference: Vegetarian" in result
        assert "Difficulty level: Easy" in result
        assert "Servings: 6" in result
        assert "Meal type: Lunch" in result

    def test_partial_preferences(self):
        """Only non-None preferences appear in the output."""
        request = _make_request(preferences={"category": "mexican", "difficulty": "Hard"})
        result = RecipeGenerationService._build_preferences_text(request)
        assert "Category: mexican" in result
        assert "Difficulty level: Hard" in result
        assert "Dietary" not in result
        assert "Servings" not in result


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------

class TestRecipeGenerationErrors:
    """Tests for error handling paths."""

    def test_empty_ai_response_raises_error(self, recipe_service):
        """Empty response from AI raises RecipeGenerationError."""
        service, mock_client = recipe_service

        empty_response = MagicMock()
        empty_response.candidates = []
        mock_client.models.generate_content.return_value = empty_response

        with pytest.raises(RecipeGenerationError, match="No response"):
            service.generate(_make_request())

    def test_invalid_json_raises_parse_error(self, recipe_service):
        """Malformed JSON raises RecipeParseError."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            "This is not valid JSON!"
        )

        with pytest.raises(RecipeParseError, match="parse"):
            service.generate(_make_request())

    def test_api_exception_raises_generation_error(self, recipe_service):
        """Exception during API call raises RecipeGenerationError."""
        service, mock_client = recipe_service

        mock_client.models.generate_content.side_effect = RuntimeError("API down")

        with pytest.raises(RecipeGenerationError, match="API down"):
            service.generate(_make_request())

    def test_import_error_raises_generation_error(self, recipe_service):
        """Missing google-genai package raises RecipeGenerationError."""
        service, mock_client = recipe_service

        with patch(
            "app.services.ai.recipe_generation.service.RecipeGenerationService.generate",
            side_effect=RecipeGenerationError("google-genai package is not installed"),
        ):
            with pytest.raises(RecipeGenerationError, match="google-genai"):
                service.generate(_make_request())

    def test_nutrition_parse_handles_empty_data(self, recipe_service):
        """Empty nutrition_facts dict returns None."""
        result = parse_nutrition_dict({})
        assert result is None

    def test_nutrition_parse_handles_none(self, recipe_service):
        """None nutrition data returns None."""
        result = parse_nutrition_dict(None)
        assert result is None

    def test_nutrition_parse_partial_data(self, recipe_service):
        """Partial nutrition data is parsed with None for missing fields."""
        result = parse_nutrition_dict({"calories": 200})
        assert result is not None
        assert result.calories == 200
        assert result.protein_g is None
        assert result.is_ai_estimated is True


# ---------------------------------------------------------------------------
# Tests — parse_recipe_dict
# ---------------------------------------------------------------------------

class TestParseRecipeDict:
    """Tests for the shared parse_recipe_dict utility."""

    def test_parse_full_recipe(self):
        """Full recipe dict is parsed correctly."""
        data = json.loads(_full_recipe_json())
        recipe = parse_recipe_dict(data)
        assert recipe.recipe_name == "Spicy Thai Green Curry"
        assert recipe.description == "A fragrant and spicy Thai green curry with vegetables."
        assert recipe.prep_time == 15
        assert recipe.cook_time == 25
        assert len(recipe.ingredients) == 2

    def test_parse_recipe_missing_name_uses_default(self):
        """Missing recipe_name falls back to 'Untitled Recipe'."""
        data = {"ingredients": [_INGREDIENT], "directions": "Cook it."}
        recipe = parse_recipe_dict(data)
        assert recipe.recipe_name == "Untitled Recipe"

    def test_parse_recipe_time_as_string(self):
        """Time values provided as strings are safely converted to int."""
        data = {
            "recipe_name": "Test",
            "prep_time": "15",
            "cook_time": "30.5",
            "ingredients": [_INGREDIENT],
            "directions": "Cook it.",
        }
        recipe = parse_recipe_dict(data)
        assert recipe.prep_time == 15
        assert recipe.cook_time == 30

    def test_parse_recipe_servings_as_string(self):
        """Servings provided as string is safely converted to int."""
        data = {
            "recipe_name": "Test",
            "servings": "4",
            "ingredients": [_INGREDIENT],
            "directions": "Cook it.",
        }
        recipe = parse_recipe_dict(data)
        assert recipe.servings == 4

    def test_parse_recipe_invalid_time_returns_none(self):
        """Invalid time values return None instead of crashing."""
        data = {
            "recipe_name": "Test",
            "prep_time": "quick",
            "cook_time": None,
            "ingredients": [_INGREDIENT],
            "directions": "Cook it.",
        }
        recipe = parse_recipe_dict(data)
        assert recipe.prep_time is None
        assert recipe.cook_time is None

    def test_parse_recipe_empty_ingredients_raises(self):
        """Empty ingredients list raises ValueError instead of parsing as valid."""
        data = {"recipe_name": "Test", "directions": "Cook it.", "ingredients": []}
        with pytest.raises(ValueError, match="ingredients"):
            parse_recipe_dict(data)

    def test_parse_recipe_missing_directions_raises(self):
        """Missing/blank directions raises ValueError instead of parsing as valid."""
        data = {"recipe_name": "Test", "ingredients": [_INGREDIENT], "directions": "   "}
        with pytest.raises(ValueError, match="directions"):
            parse_recipe_dict(data)


# ---------------------------------------------------------------------------
# Tests — _safe_int / _safe_float
# ---------------------------------------------------------------------------

class TestSafeConversions:
    """Tests for _safe_int and _safe_float helper functions."""

    # _safe_int
    def test_safe_int_from_int(self):
        assert safe_int(42) == 42

    def test_safe_int_from_float(self):
        assert safe_int(42.9) == 42

    def test_safe_int_from_string(self):
        assert safe_int("42") == 42

    def test_safe_int_from_float_string(self):
        assert safe_int("42.7") == 42

    def test_safe_int_none(self):
        assert safe_int(None) is None

    def test_safe_int_invalid(self):
        assert safe_int("not a number") is None

    def test_safe_int_empty_string(self):
        assert safe_int("") is None

    # _safe_float
    def test_safe_float_from_float(self):
        assert safe_float(12.5) == 12.5

    def test_safe_float_from_int(self):
        assert safe_float(12) == 12.0

    def test_safe_float_from_string(self):
        assert safe_float("12.5") == 12.5

    def test_safe_float_none(self):
        assert safe_float(None) is None

    def test_safe_float_invalid(self):
        assert safe_float("abc") is None

    def test_safe_float_rounds_to_one_decimal(self):
        assert safe_float(12.456) == 12.5

    def test_safe_float_empty_string(self):
        assert safe_float("") is None
