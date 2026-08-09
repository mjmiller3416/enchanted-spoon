"""Service for estimating recipe nutrition facts using Gemini."""

import json
import logging
import re
from typing import Optional

from app.dtos.nutrition_dtos import (
    NutritionEstimationRequestDTO,
    NutritionEstimationResponseDTO,
)
from app.services.ai.config import GEMINI_MODEL
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.parse_utils import parse_nutrition_dict
from app.services.ai.response_utils import extract_text_from_response

logger = logging.getLogger(__name__)

# ── Model settings ───────────────────────────────────────────────────────
MODEL_NAME = GEMINI_MODEL
TEMPERATURE = 0.3  # Low temperature for factual accuracy
MAX_OUTPUT_TOKENS = 1024

# Environment variable for API key
API_KEY_ENV_VAR = "GEMINI_NUTRITION_API_KEY"

# Prompt template for estimating nutrition facts
PROMPT_TEMPLATE = """You are a professional nutritionist. Estimate the nutrition facts PER SERVING for this recipe.

Recipe: {recipe_name}
Servings: {servings}

Ingredients:
{ingredients_text}

Return ONLY valid JSON with these exact fields (all numeric values, no units in values):
{{
  "calories": <integer or null>,
  "protein_g": <float or null>,
  "total_fat_g": <float or null>,
  "saturated_fat_g": <float or null>,
  "trans_fat_g": <float or null>,
  "cholesterol_mg": <float or null>,
  "sodium_mg": <float or null>,
  "total_carbs_g": <float or null>,
  "dietary_fiber_g": <float or null>,
  "total_sugars_g": <float or null>
}}

Be realistic and base estimates on standard USDA nutrition data. Round to 1 decimal place for grams, whole numbers for mg and calories. Return ONLY the JSON object, no other text."""


def _extract_json(text: str) -> dict:
    """Parse JSON from model output, handling markdown fences and surrounding text."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the first {...} block
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise json.JSONDecodeError("No valid JSON object found in response", text, 0)


class NutritionEstimationService:
    """Service for estimating nutrition facts using Gemini AI."""

    def __init__(self) -> None:
        """Initialize the nutrition estimation service."""
        get_gemini_client(API_KEY_ENV_VAR)

    def estimate(
        self, request: NutritionEstimationRequestDTO
    ) -> NutritionEstimationResponseDTO:
        """Estimate nutrition facts for a recipe based on its ingredients.

        Args:
            request: The estimation request with recipe name, ingredients, and servings.

        Returns:
            NutritionEstimationResponseDTO with estimated nutrition facts or error.
        """
        try:
            client = get_gemini_client(API_KEY_ENV_VAR)

            # Build ingredients text
            ingredients_lines = []
            for ing in request.ingredients:
                parts = []
                if ing.quantity:
                    parts.append(str(ing.quantity))
                if ing.unit:
                    parts.append(ing.unit)
                parts.append(ing.ingredient_name)
                ingredients_lines.append("- " + " ".join(parts))

            ingredients_text = "\n".join(ingredients_lines) or "- No ingredients provided"
            servings = request.servings or 1

            prompt = PROMPT_TEMPLATE.format(
                recipe_name=request.recipe_name,
                servings=servings,
                ingredients_text=ingredients_text,
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={
                    "temperature": TEMPERATURE,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "response_mime_type": "application/json",
                    "thinking_config": {"thinking_budget": 0},
                },
            )

            raw_text = extract_text_from_response(response)
            if not raw_text:
                return NutritionEstimationResponseDTO(
                    success=False, error="No response from AI model"
                )

            logger.debug(f"[Nutrition] Raw response: {raw_text[:500]}")
            data = _extract_json(raw_text)

            nutrition = parse_nutrition_dict(data)

            if nutrition:
                logger.info(
                    f"[Nutrition] Estimated for '{request.recipe_name}': "
                    f"{nutrition.calories} cal, {nutrition.protein_g}g protein"
                )

            return NutritionEstimationResponseDTO(
                success=True, nutrition_facts=nutrition
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Nutrition] JSON parse error: {e}")
            return NutritionEstimationResponseDTO(
                success=False, error="Failed to parse nutrition data from AI response"
            )
        except Exception as e:
            logger.error(f"[Nutrition] Estimation failed: {e}")
            return NutritionEstimationResponseDTO(
                success=False, error=f"Nutrition estimation failed: {str(e)}"
            )


# Singleton instance
_service_instance: Optional[NutritionEstimationService] = None


def get_nutrition_estimation_service() -> NutritionEstimationService:
    """Get the singleton instance of the nutrition estimation service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = NutritionEstimationService()
    return _service_instance
