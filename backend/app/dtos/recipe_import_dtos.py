"""app/dtos/recipe_import_dtos.py

Pydantic DTOs for importing a recipe from a website URL.
The response mirrors RecipeGenerationResponseDTO's shape (recipe, nutrition,
base64 image fields) so the frontend wizard can prefill from either flow.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .nutrition_dtos import NutritionFactsDTO
from .recipe_generation_dtos import RecipeGeneratedDTO


# ── Request DTO ──────────────────────────────────────────────────────────────


class RecipeImportRequestDTO(BaseModel):
    """Request DTO for importing a recipe from a URL."""

    url: str = Field(..., min_length=1, max_length=2048)
    allowed_categories: List[str] = Field(default_factory=list)
    include_source_image: bool = True
    # Caption or recipe text pasted after a TikTok/Instagram post could not
    # be read. Only used for social URLs. Blank is treated as omitted.
    pasted_text: Optional[str] = Field(None, max_length=8000)

    @field_validator("pasted_text")
    @classmethod
    def blank_pasted_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


# ── Response DTO ─────────────────────────────────────────────────────────────


class RecipeImportResponseDTO(BaseModel):
    """Response DTO for a recipe imported from a URL."""

    success: bool
    recipe: Optional[RecipeGeneratedDTO] = None
    # Nutrition from the site's own structured data (is_ai_estimated=False);
    # None when the site publishes none — the wizard's AI estimation remains available.
    nutrition_facts: Optional[NutritionFactsDTO] = None
    source_url: Optional[str] = None
    # Recipe photo downloaded from the source page, base64-encoded — same field
    # names as RecipeGenerationResponseDTO so both flows share the upload path.
    reference_image_data: Optional[str] = None
    banner_image_data: Optional[str] = None
    error: Optional[str] = None
