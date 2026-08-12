"""Service for generating meal-specific cooking tips using Gemini."""

import logging
from typing import Optional

from app.dtos.meal_suggestions_dtos import (
    MealSuggestionsRequestDTO,
    MealSuggestionsResponseDTO,
)
from app.services.ai.config import GEMINI_MODEL
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.response_utils import extract_text_from_response
from app.services.ai.text_utils import clean_tip

logger = logging.getLogger(__name__)

# ── Model settings ───────────────────────────────────────────────────────
MODEL_NAME = GEMINI_MODEL
TEMPERATURE = 0.8  # Varied tips
MAX_OUTPUT_TOKENS = 150  # Just need a short tip

# Environment variable for API key (reuses existing tip key)
API_KEY_ENV_VAR = "GEMINI_TIP_API_KEY"
API_KEY_ENV_VAR_ALT = "GEMINI_COOKING_TIP_API_KEY"

# System prompt for generating meal-specific cooking tip
MEAL_TIP_PROMPT = """You are Genie: a friendly chef-buddy who gives ONE quick "upgrade idea" for a specific dish.

Goal: Suggest a small enhancement that makes the dish taste better, feel more special, or more fun to eat.
This is NOT a basic cooking lesson.

RULES:
- Give ONE upgrade idea (1-2 sentences).
- It must be specific to THIS dish (not generic advice like "season well" or "don't overcook").
- Prefer upgrades like: sauce ideas, toppings, mix-ins, seasoning twists, texture boosts, better assembly, a side pairing, or a "make it restaurant-y" finishing touch.
- Include at least one concrete detail (ingredient, amount, timing, or method).
- Assume a normal home kitchen; no specialty equipment required.
- Avoid food-safety reminders and vague technique tips unless absolutely necessary for the dish.
- Do not use prefixes like "Tip:" and do not use JSON.

QUALITY CHECK (do silently):
If your suggestion could apply to 10+ unrelated dishes, rewrite it to be more dish-specific.

Return ONLY the suggestion text."""


class MealSuggestionsService:
    """Service for generating meal-specific cooking tips."""

    def __init__(self) -> None:
        """Initialize the meal suggestions service."""
        # Validate eagerly so we fail fast if misconfigured
        get_gemini_client(API_KEY_ENV_VAR, API_KEY_ENV_VAR_ALT)

    def generate_suggestions(
        self, request: MealSuggestionsRequestDTO
    ) -> MealSuggestionsResponseDTO:
        """Generate a cooking tip for a meal.

        Args:
            request: The meal details to generate a tip for.

        Returns:
            MealSuggestionsResponseDTO with tip or error.
        """
        try:
            client = get_gemini_client(API_KEY_ENV_VAR, API_KEY_ENV_VAR_ALT)

            # Build context for the dish
            category_text = f" ({request.main_recipe_category})" if request.main_recipe_category else ""
            meal_type_text = f" for {request.meal_type}" if request.meal_type else ""

            user_prompt = f"Dish: {request.main_recipe_name}{category_text}{meal_type_text}"

            # Generate tip
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    {"role": "user", "parts": [{"text": MEAL_TIP_PROMPT}]},
                    {"role": "model", "parts": [{"text": "I understand. I'll provide a concise, practical cooking tip."}]},
                    {"role": "user", "parts": [{"text": user_prompt}]},
                ],
                config={
                    "temperature": TEMPERATURE,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "thinking_config": {"thinking_budget": 0},
                },
            )

            # Extract text from response
            tip_text = extract_text_from_response(response)
            if tip_text:
                tip_text = clean_tip(tip_text)

                logger.info(
                    f"[MealSuggestions] Generated tip for: {request.main_recipe_name}"
                )

                return MealSuggestionsResponseDTO(
                    success=True,
                    cooking_tip=tip_text,
                    error=None,
                )

            return MealSuggestionsResponseDTO(
                success=False,
                cooking_tip=None,
                error="Could not generate tip from AI response",
            )

        except Exception as e:
            logger.error(f"[MealSuggestions] Error generating tip: {e}")
            return MealSuggestionsResponseDTO(
                success=False,
                cooking_tip=None,
                error=str(e),
            )


# Singleton instance
_service_instance: Optional[MealSuggestionsService] = None


def get_meal_suggestions_service() -> MealSuggestionsService:
    """Get the singleton instance of the meal suggestions service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MealSuggestionsService()
    return _service_instance
