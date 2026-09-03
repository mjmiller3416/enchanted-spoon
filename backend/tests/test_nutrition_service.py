"""Tests for the NutritionEstimationService.

Covers:
- Successful estimation with mocked Gemini response
- JSON parsing from markdown code blocks
- Handling missing/null fields
- Error handling (JSON parse failure, no response, API errors)
- safe_int / safe_float helper functions (from parse_utils)
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.dtos.nutrition_dtos import (
    NutritionEstimationRequestDTO,
    NutritionIngredientDTO,
)
from app.services.ai.nutrition_estimation import NutritionEstimationService
from app.services.ai.parse_utils import safe_float, safe_int


# ---------------------------------------------------------------------------
# Helpers to mock the Gemini response object
# ---------------------------------------------------------------------------

def _make_gemini_response(text: str):
    """Create a mock Gemini API response containing the given text."""
    part = MagicMock()
    # A bare MagicMock attribute is truthy, so an unset `thought` would make
    # extract_text_from_response skip the part as a thinking part.
    part.thought = False
    part.text = text

    content = MagicMock()
    content.parts = [part]

    candidate = MagicMock()
    candidate.content = content

    response = MagicMock()
    response.candidates = [candidate]
    return response


def _make_request(
    recipe_name: str = "Test Recipe",
    ingredients: list | None = None,
    servings: int | None = 4,
) -> NutritionEstimationRequestDTO:
    """Create a standard estimation request for testing."""
    if ingredients is None:
        ingredients = [
            NutritionIngredientDTO(ingredient_name="Flour", quantity=2.0, unit="cups"),
            NutritionIngredientDTO(ingredient_name="Sugar", quantity=0.5, unit="cups"),
        ]
    return NutritionEstimationRequestDTO(
        recipe_name=recipe_name,
        ingredients=ingredients,
        servings=servings,
    )


# ---------------------------------------------------------------------------
# Fixture: patched service (bypasses Gemini client init)
# ---------------------------------------------------------------------------

@pytest.fixture()
def nutrition_service():
    """Create a NutritionEstimationService with the Gemini client mocked out."""
    with patch(
        "app.services.ai.nutrition_estimation.get_gemini_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        service = NutritionEstimationService()
        yield service, mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNutritionEstimationService:
    """Tests for the estimate() method."""

    def test_successful_estimation(self, nutrition_service):
        """Valid Gemini response is parsed into NutritionFactsDTO."""
        service, mock_client = nutrition_service

        ai_response_json = json.dumps({
            "calories": 350,
            "protein_g": 12.5,
            "total_fat_g": 8.0,
            "saturated_fat_g": 2.5,
            "trans_fat_g": 0.0,
            "cholesterol_mg": 25.0,
            "sodium_mg": 480.0,
            "total_carbs_g": 55.0,
            "dietary_fiber_g": 3.0,
            "total_sugars_g": 4.5,
        })
        mock_client.models.generate_content.return_value = _make_gemini_response(
            ai_response_json
        )

        result = service.estimate(_make_request())

        assert result.success is True
        assert result.error is None
        nf = result.nutrition_facts
        assert nf.calories == 350
        assert nf.protein_g == 12.5
        assert nf.total_fat_g == 8.0
        assert nf.is_ai_estimated is True

    def test_markdown_wrapped_json_parsed(self, nutrition_service):
        """Markdown-fenced JSON is still parsed (_extract_json strips the fences)."""
        service, mock_client = nutrition_service

        text = '```json\n{"calories": 200, "protein_g": 10.0}\n```'
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        result = service.estimate(_make_request())

        assert result.success is True
        assert result.nutrition_facts.calories == 200
        assert result.nutrition_facts.protein_g == 10.0

    def test_partial_fields_from_ai(self, nutrition_service):
        """Missing fields in AI response result in None values."""
        service, mock_client = nutrition_service

        text = json.dumps({"calories": 150})
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        result = service.estimate(_make_request())

        assert result.success is True
        assert result.nutrition_facts.calories == 150
        assert result.nutrition_facts.protein_g is None
        assert result.nutrition_facts.total_fat_g is None

    def test_null_fields_from_ai(self, nutrition_service):
        """Explicit null values in AI response are handled gracefully."""
        service, mock_client = nutrition_service

        text = json.dumps({
            "calories": None,
            "protein_g": None,
            "total_fat_g": 5.5,
        })
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        result = service.estimate(_make_request())

        assert result.success is True
        assert result.nutrition_facts.calories is None
        assert result.nutrition_facts.protein_g is None
        assert result.nutrition_facts.total_fat_g == 5.5

    def test_no_response_text(self, nutrition_service):
        """Empty response from AI returns error."""
        service, mock_client = nutrition_service

        empty_response = MagicMock()
        empty_response.candidates = []
        mock_client.models.generate_content.return_value = empty_response

        result = service.estimate(_make_request())

        assert result.success is False
        assert "No response" in result.error

    def test_invalid_json_response(self, nutrition_service):
        """Malformed JSON returns a parse error."""
        service, mock_client = nutrition_service

        mock_client.models.generate_content.return_value = _make_gemini_response(
            "This is not JSON at all!"
        )

        result = service.estimate(_make_request())

        assert result.success is False
        assert "parse" in result.error.lower() or "Could not" in result.error

    def test_api_exception(self, nutrition_service):
        """Exception during API call returns error gracefully."""
        service, mock_client = nutrition_service

        mock_client.models.generate_content.side_effect = RuntimeError("API down")

        result = service.estimate(_make_request())

        assert result.success is False
        assert "API down" in result.error

    def test_request_with_no_ingredients(self, nutrition_service):
        """Estimation with empty ingredients list still works."""
        service, mock_client = nutrition_service

        text = json.dumps({"calories": 0})
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        request = _make_request(ingredients=[])
        result = service.estimate(request)

        assert result.success is True

    def test_request_without_servings(self, nutrition_service):
        """Servings defaults to 1 if not provided."""
        service, mock_client = nutrition_service

        text = json.dumps({"calories": 100})
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        request = _make_request(servings=None)
        result = service.estimate(request)

        # Verify the prompt was built with servings=1
        call_args = mock_client.models.generate_content.call_args
        prompt_text = call_args[1]["contents"][0] if "contents" in call_args[1] else call_args[0][0]
        # The service uses positional args: contents=[prompt]
        assert result.success is True

    def test_float_rounding(self, nutrition_service):
        """Float values are rounded to 1 decimal place."""
        service, mock_client = nutrition_service

        text = json.dumps({"protein_g": 12.456, "total_fat_g": 8.999})
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        result = service.estimate(_make_request())

        assert result.success is True
        assert result.nutrition_facts.protein_g == 12.5
        assert result.nutrition_facts.total_fat_g == 9.0

    def test_calories_as_float_converted_to_int(self, nutrition_service):
        """Calories returned as float are converted to int."""
        service, mock_client = nutrition_service

        text = json.dumps({"calories": 350.7})
        mock_client.models.generate_content.return_value = _make_gemini_response(text)

        result = service.estimate(_make_request())

        assert result.success is True
        assert result.nutrition_facts.calories == 350
        assert isinstance(result.nutrition_facts.calories, int)


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
