"""Shared parsing utilities for AI services.

Type-safe conversion helpers and common DTO construction logic
used across recipe generation, nutrition estimation, and other AI services.
"""

from typing import Optional

from app.dtos.nutrition_dtos import NutritionFactsDTO
from app.dtos.recipe_generation_dtos import GeneratedIngredientDTO, RecipeGeneratedDTO


def safe_int(value: object) -> Optional[int]:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_float(value: object) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except (ValueError, TypeError):
        return None


def parse_nutrition_dict(data: dict) -> Optional[NutritionFactsDTO]:
    """Parse a nutrition facts dictionary into a NutritionFactsDTO.

    Handles missing fields and type coercion from AI responses
    where values may arrive as strings, floats, or nulls.

    Args:
        data: Raw nutrition facts dictionary from an AI response.

    Returns:
        A NutritionFactsDTO with is_ai_estimated=True, or None if data is empty/falsy.
    """
    if not data:
        return None

    return NutritionFactsDTO(
        calories=safe_int(data.get("calories")),
        protein_g=safe_float(data.get("protein_g")),
        total_fat_g=safe_float(data.get("total_fat_g")),
        saturated_fat_g=safe_float(data.get("saturated_fat_g")),
        trans_fat_g=safe_float(data.get("trans_fat_g")),
        cholesterol_mg=safe_float(data.get("cholesterol_mg")),
        sodium_mg=safe_float(data.get("sodium_mg")),
        total_carbs_g=safe_float(data.get("total_carbs_g")),
        dietary_fiber_g=safe_float(data.get("dietary_fiber_g")),
        total_sugars_g=safe_float(data.get("total_sugars_g")),
        is_ai_estimated=True,
    )


def parse_recipe_dict(data: dict) -> RecipeGeneratedDTO:
    """Parse a recipe dictionary from an AI response into a RecipeGeneratedDTO.

    Handles missing fields, type coercion for time/servings values,
    and ingredient list construction. Used by both the recipe generation
    service and the assistant's recipe generation flow.

    Args:
        data: Raw recipe dictionary from an AI JSON response.

    Returns:
        A fully populated RecipeGeneratedDTO with safe defaults for missing fields.

    Raises:
        ValueError: If the response has no ingredients or no directions —
            a malformed or partial AI response, not a valid recipe.
    """
    ingredients = [
        GeneratedIngredientDTO(**ing)
        for ing in data.get("ingredients", [])
    ]
    if not ingredients:
        raise ValueError("AI response contained no ingredients")

    directions = data.get("directions")
    if not directions or not str(directions).strip():
        raise ValueError("AI response contained no directions")

    return RecipeGeneratedDTO(
        recipe_name=data.get("recipe_name", "Untitled Recipe"),
        recipe_category=data.get("recipe_category", "other"),
        meal_type=data.get("meal_type", "dinner"),
        diet_pref=data.get("diet_pref", "none"),
        description=data.get("description"),
        prep_time=safe_int(data.get("prep_time")),
        cook_time=safe_int(data.get("cook_time")),
        difficulty=data.get("difficulty"),
        servings=safe_int(data.get("servings")),
        directions=data.get("directions"),
        notes=data.get("notes"),
        ingredients=ingredients,
    )
