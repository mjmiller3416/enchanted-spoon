"""Service for generating complete recipes using Gemini AI."""

import json
import logging
from typing import Awaitable, Callable, Optional

from app.dtos.nutrition_dtos import NutritionFactsDTO
from app.dtos.recipe_generation_dtos import (
    RecipeGeneratedDTO,
    RecipeGenerationRequestDTO,
    RecipeGenerationResponseDTO,
)
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.provider_errors import safe_ai_error
from app.services.ai.parse_utils import parse_nutrition_dict, parse_recipe_dict
from app.services.ai.response_utils import extract_text_from_response

from .config import (
    API_KEY_ENV_VAR,
    DEFAULT_CATEGORIES,
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    NUTRITION_SCHEMA,
    PROMPT_TEMPLATE,
    TEMPERATURE,
)

logger = logging.getLogger(__name__)


# ── Domain Exceptions ────────────────────────────────────────────────────────


class RecipeGenerationError(Exception):
    """Raised when recipe generation fails."""

    pass


class RecipeParseError(Exception):
    """Raised when AI response cannot be parsed."""

    pass


# ── Service ──────────────────────────────────────────────────────────────────


class RecipeGenerationService:
    """Service for generating complete recipes using Gemini AI."""

    def __init__(self) -> None:
        """Initialize the recipe generation service."""
        get_gemini_client(API_KEY_ENV_VAR)

    async def generate(
        self, request: RecipeGenerationRequestDTO,
        image_generator: Optional[Callable[[str], Awaitable[tuple[Optional[str], Optional[str]]]]] = None,
    ) -> RecipeGenerationResponseDTO:
        """Generate a complete recipe from a user prompt and optional preferences.

        Args:
            request: The generation request with prompt, preferences, and flags.
            image_generator: Caller-supplied metered callback; absent means no images.

        Returns:
            RecipeGenerationResponseDTO with recipe data, optional nutrition and images.

        Raises:
            RecipeGenerationError: If the generation process fails entirely.
            RecipeParseError: If the AI response cannot be parsed.
        """
        try:
            client = get_gemini_client(API_KEY_ENV_VAR)

            # Build preferences text
            preferences_text = self._build_preferences_text(request)

            # Include nutrition schema in prompt if requested
            nutrition_schema = NUTRITION_SCHEMA if request.estimate_nutrition else ""

            # Build allowed categories string from request or defaults
            categories = request.allowed_categories or DEFAULT_CATEGORIES
            allowed_categories = "|".join(categories)

            prompt = PROMPT_TEMPLATE.format(
                prompt=request.prompt,
                preferences_text=preferences_text,
                nutrition_schema=nutrition_schema,
                allowed_categories=allowed_categories,
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
                raise RecipeGenerationError("No response from AI model")

            data = json.loads(raw_text)

            # Parse recipe using shared utility
            recipe = parse_recipe_dict(data)

            # Parse nutrition if included
            nutrition_facts: Optional[NutritionFactsDTO] = None
            if request.estimate_nutrition and "nutrition_facts" in data:
                nutrition_facts = parse_nutrition_dict(data["nutrition_facts"])

            logger.info(
                f"[RecipeGeneration] Generated recipe '{recipe.recipe_name}' "
                f"with {len(recipe.ingredients)} ingredients"
            )

            # Optional image generation
            reference_image_data: Optional[str] = None
            banner_image_data: Optional[str] = None
            if request.generate_image and image_generator is not None:
                try:
                    reference_image_data, banner_image_data = await image_generator(recipe.recipe_name)
                except Exception:
                    # Optional photo failures must never discard a usable recipe.
                    logger.warning("Optional recipe photo generation failed")

            return RecipeGenerationResponseDTO(
                success=True,
                recipe=recipe,
                nutrition_facts=nutrition_facts,
                reference_image_data=reference_image_data,
                banner_image_data=banner_image_data,
            )

        except json.JSONDecodeError as e:
            safe_ai_error(e, "RecipeGeneration")
            failure = RecipeParseError("Failed to parse recipe data from AI response")
        except ValueError as e:
            safe_ai_error(e, "RecipeGeneration")
            failure = RecipeParseError("Invalid recipe data from AI response")
        except (RecipeGenerationError, RecipeParseError):
            raise
        except ImportError as e:
            safe_ai_error(e, "RecipeGeneration")
            failure = RecipeGenerationError("AI features are temporarily unavailable. Please try again later.")
        except Exception as e:
            failure = RecipeGenerationError(safe_ai_error(e, "RecipeGeneration"))

        # Raise after leaving the handler: `from None` inside it would still retain
        # the raw provider error in __context__, accessible to error-reporting SDKs.
        raise failure from None

    # ── Private Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _build_preferences_text(request: RecipeGenerationRequestDTO) -> str:
        """Build a preferences section for the prompt."""
        if not request.preferences:
            return ""

        prefs = request.preferences
        lines: list[str] = []
        if prefs.category:
            lines.append(f"Category: {prefs.category}")
        if prefs.dietary:
            lines.append(f"Dietary preference: {prefs.dietary}")
        if prefs.difficulty:
            lines.append(f"Difficulty level: {prefs.difficulty}")
        if prefs.servings:
            lines.append(f"Servings: {prefs.servings}")
        if prefs.meal_type:
            lines.append(f"Meal type: {prefs.meal_type}")

        if not lines:
            return ""
        return "\nPreferences:\n" + "\n".join(f"- {line}" for line in lines)



_service_instance: Optional[RecipeGenerationService] = None


def get_recipe_generation_service() -> RecipeGenerationService:
    """Get the singleton instance of the recipe generation service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RecipeGenerationService()
    return _service_instance
