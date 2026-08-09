"""app/core/dtos/nutrition_dtos.py

Pydantic DTOs for nutrition facts operations and AI estimation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from ..models.nutrition_facts import NutritionFacts


# ── Nutrition Facts DTOs ───────────────────────────────────────────────────────

class NutritionFactsDTO(BaseModel):
    """DTO for creating/updating nutrition facts on a recipe."""

    model_config = ConfigDict(from_attributes=True)

    calories: Optional[int] = Field(None, ge=0)
    protein_g: Optional[float] = Field(None, ge=0)
    total_fat_g: Optional[float] = Field(None, ge=0)
    saturated_fat_g: Optional[float] = Field(None, ge=0)
    trans_fat_g: Optional[float] = Field(None, ge=0)
    cholesterol_mg: Optional[float] = Field(None, ge=0)
    sodium_mg: Optional[float] = Field(None, ge=0)
    total_carbs_g: Optional[float] = Field(None, ge=0)
    dietary_fiber_g: Optional[float] = Field(None, ge=0)
    total_sugars_g: Optional[float] = Field(None, ge=0)
    is_ai_estimated: bool = False


class NutritionFactsResponseDTO(NutritionFactsDTO):
    """DTO for nutrition facts in API responses."""

    id: int
    recipe_id: int

    @classmethod
    def from_model(cls, model: "NutritionFacts") -> "NutritionFactsResponseDTO":
        """Convert a NutritionFacts model to response DTO."""
        return cls(
            id=model.id,
            recipe_id=model.recipe_id,
            calories=model.calories,
            protein_g=model.protein_g,
            total_fat_g=model.total_fat_g,
            saturated_fat_g=model.saturated_fat_g,
            trans_fat_g=model.trans_fat_g,
            cholesterol_mg=model.cholesterol_mg,
            sodium_mg=model.sodium_mg,
            total_carbs_g=model.total_carbs_g,
            dietary_fiber_g=model.dietary_fiber_g,
            total_sugars_g=model.total_sugars_g,
            is_ai_estimated=model.is_ai_estimated,
        )


# ── AI Estimation DTOs ────────────────────────────────────────────────────────

class NutritionIngredientDTO(BaseModel):
    """Simplified ingredient for nutrition estimation requests."""

    ingredient_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None


class NutritionEstimationRequestDTO(BaseModel):
    """Request DTO for AI-powered nutrition estimation."""

    recipe_name: str
    ingredients: List[NutritionIngredientDTO] = Field(..., max_length=100)
    servings: Optional[int] = Field(None, ge=1)


class NutritionEstimationResponseDTO(BaseModel):
    """Response DTO for AI-powered nutrition estimation."""

    success: bool
    nutrition_facts: Optional[NutritionFactsDTO] = None
    error: Optional[str] = None
