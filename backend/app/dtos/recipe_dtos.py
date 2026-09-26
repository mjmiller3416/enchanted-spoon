"""app/core/dtos/recipe_dtos.py

Pydantic DTOs for recipe operations and data transfer.
Handles recipe creation, updates, filtering, and responses with ingredient relationships.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .nutrition_dtos import NutritionFactsDTO, NutritionFactsResponseDTO

if TYPE_CHECKING:
    from ..models.recipe import Recipe


# ── Recipe Ingredient DTOs ──────────────────────────────────────────────────────────────────────────────────
class RecipeIngredientDTO(BaseModel):
    """DTO describing an ingredient entry within a recipe."""

    model_config = ConfigDict(from_attributes=True)

    existing_ingredient_id: Optional[int] = None
    # Bounded by the shopping list columns these flow into (see ShoppingItem)
    ingredient_name: str = Field(..., min_length=1, max_length=200)
    ingredient_category: str = Field(..., min_length=1, max_length=100)
    quantity: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)

    @field_validator("ingredient_name", "ingredient_category", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

# ── Base DTOs ───────────────────────────────────────────────────────────────────────────────────────────────
class RecipeBaseDTO(BaseModel):
    """Base DTO for recipe operations."""

    model_config = ConfigDict(from_attributes=True)

    recipe_name: str = Field(..., min_length=1)
    recipe_category: str = Field(..., min_length=1)
    meal_type: str = Field(default="Dinner", min_length=1)
    diet_pref: Optional[str] = None  # match the model field name
    description: Optional[str] = None
    prep_time: Optional[int] = Field(None, ge=0)
    cook_time: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    difficulty: Optional[str] = None
    directions: Optional[str] = None
    notes: Optional[str] = None
    reference_image_path: Optional[str] = None
    banner_image_path: Optional[str] = None
    source_url: Optional[str] = Field(None, max_length=2048)

    @field_validator("recipe_name", "recipe_category", "meal_type", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("difficulty", mode="before")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Easy", "Medium", "Hard"):
            raise ValueError("difficulty must be Easy, Medium, or Hard")
        return v

# ── Recipe Card DTO ─────────────────────────────────────────────────────────────────────────────────────────
class RecipeCardDTO(BaseModel):
    """Minimal recipe info needed to render a recipe card."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_name: str
    is_favorite: bool = False
    is_ai_generated: bool = False
    is_sample: bool = False
    source_url: Optional[str] = None
    reference_image_path: Optional[str] = None
    banner_image_path: Optional[str] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    total_time: Optional[int] = None
    # Optional metadata for badge display
    recipe_category: Optional[str] = None
    meal_type: Optional[str] = None
    diet_pref: Optional[str] = None
    difficulty: Optional[str] = None
    # Cooking stats (populated when needed)
    times_cooked: Optional[int] = None
    last_cooked: Optional[str] = None  # ISO datetime string
    created_at: Optional[str] = None  # ISO datetime string - when recipe was added

    @classmethod
    def from_recipe(
        cls,
        recipe: Optional[Recipe],
        times_cooked: Optional[int] = None,
        last_cooked: Optional[str] = None,
    ) -> Optional["RecipeCardDTO"]:
        """Convert a Recipe model to RecipeCardDTO."""
        if recipe is None:
            return None
        return cls(
            id=recipe.id,
            recipe_name=recipe.recipe_name,
            is_favorite=recipe.is_favorite,
            is_ai_generated=recipe.is_ai_generated,
            is_sample=bool(recipe.is_sample),
            source_url=recipe.source_url,
            reference_image_path=recipe.reference_image_path,
            banner_image_path=recipe.banner_image_path,
            servings=recipe.servings,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            total_time=recipe.total_time,
            recipe_category=recipe.recipe_category,
            meal_type=recipe.meal_type,
            diet_pref=recipe.diet_pref,
            difficulty=recipe.difficulty,
            times_cooked=times_cooked,
            last_cooked=last_cooked,
            created_at=recipe.created_at.isoformat() if recipe.created_at else None,
        )

# ── Create DTO ──────────────────────────────────────────────────────────────────────────────────────────────
class RecipeCreateDTO(RecipeBaseDTO):
    """DTO used to create a new recipe with ingredients."""
    # Input-only caps (response DTOs share RecipeBaseDTO and must not reject stored rows)
    recipe_name: str = Field(..., min_length=1, max_length=255)
    recipe_category: str = Field(..., min_length=1, max_length=100)
    meal_type: str = Field(default="Dinner", min_length=1, max_length=50)
    ingredients: List[RecipeIngredientDTO] = []
    is_ai_generated: bool = False
    nutrition_facts: Optional[NutritionFactsDTO] = None

# ── Update DTO ──────────────────────────────────────────────────────────────────────────────────────────────
class RecipeUpdateDTO(BaseModel):
    """DTO used to update a recipe's core attributes and ingredient list."""

    model_config = ConfigDict(from_attributes=True)

    recipe_name: Optional[str] = Field(None, min_length=1, max_length=255)
    recipe_category: Optional[str] = Field(None, min_length=1, max_length=100)
    meal_type: Optional[str] = Field(None, min_length=1, max_length=50)
    diet_pref: Optional[str] = None
    description: Optional[str] = None
    prep_time: Optional[int] = Field(None, ge=0)
    cook_time: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    difficulty: Optional[str] = Field(None, max_length=20)
    directions: Optional[str] = None
    notes: Optional[str] = None
    reference_image_path: Optional[str] = None
    banner_image_path: Optional[str] = None
    ingredients: Optional[List[RecipeIngredientDTO]] = None
    is_favorite: Optional[bool] = None
    nutrition_facts: Optional[NutritionFactsDTO] = None

    @field_validator("recipe_name", "recipe_category", "meal_type", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str) and v:
            return v.strip()
        return v

    @field_validator("difficulty", mode="before")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Easy", "Medium", "Hard"):
            raise ValueError("difficulty must be Easy, Medium, or Hard")
        return v

# ── Response DTO ────────────────────────────────────────────────────────────────────────────────────────────
class RecipeIngredientResponseDTO(BaseModel):
    """DTO for ingredient in recipe response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_name: str
    ingredient_category: str
    quantity: Optional[float] = None
    unit: Optional[str] = None

class RecipeResponseDTO(RecipeBaseDTO):
    """DTO for recipe responses with full ingredient information."""

    id: int
    total_time: Optional[int] = None
    is_favorite: bool = False
    is_ai_generated: bool = False
    is_sample: bool = False
    created_at: Optional[str] = None  # ISO format datetime string
    ingredients: List["RecipeIngredientResponseDTO"] = []
    group_ids: List[int] = []  # IDs of recipe groups this recipe belongs to
    nutrition_facts: Optional[NutritionFactsResponseDTO] = None

    @classmethod
    def from_recipe(cls, recipe: "Recipe") -> "RecipeResponseDTO":
        """Convert a Recipe model to RecipeResponseDTO."""
        ingredients = [
            RecipeIngredientResponseDTO(
                id=ri.ingredient.id,
                ingredient_name=ri.ingredient.ingredient_name,
                ingredient_category=ri.ingredient.ingredient_category,
                quantity=ri.quantity,
                unit=ri.unit,
            )
            for ri in recipe.ingredients
        ]
        group_ids = [g.id for g in recipe.groups] if recipe.groups else []

        nutrition = None
        if recipe.nutrition_facts:
            nutrition = NutritionFactsResponseDTO.from_model(recipe.nutrition_facts)

        return cls(
            id=recipe.id,
            recipe_name=recipe.recipe_name,
            recipe_category=recipe.recipe_category,
            meal_type=recipe.meal_type,
            diet_pref=recipe.diet_pref,
            description=recipe.description,
            total_time=recipe.total_time,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            servings=recipe.servings,
            difficulty=recipe.difficulty,
            directions=recipe.directions,
            notes=recipe.notes,
            reference_image_path=recipe.reference_image_path,
            banner_image_path=recipe.banner_image_path,
            source_url=recipe.source_url,
            is_favorite=recipe.is_favorite,
            is_ai_generated=recipe.is_ai_generated,
            is_sample=bool(recipe.is_sample),
            created_at=recipe.created_at.isoformat() if recipe.created_at else None,
            ingredients=ingredients,
            group_ids=group_ids,
            nutrition_facts=nutrition,
        )

# ── Filter DTO ──────────────────────────────────────────────────────────────────────────────────────────────
class RecipeFilterDTO(BaseModel):
    """DTO for filtering recipe queries."""

    model_config = ConfigDict(from_attributes=True)

    recipe_category: Optional[str] = None
    meal_type: Optional[str] = None
    diet_pref: Optional[str] = None
    cook_time: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    sort_by: Optional[str] = Field(
        None, pattern="^(recipe_name|created_at|total_time|servings)$")
    sort_order: Optional[str] = Field(
        "asc", pattern="^(asc|desc)$")
    favorites_only: bool = False
    search_term: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=100)
    offset: Optional[int] = Field(None, ge=0)
