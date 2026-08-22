"""app/core/dtos/data_management_dtos.py

Pydantic DTOs for data management operations (import/export).
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .recipe_dtos import RecipeIngredientDTO


# ── Enums ───────────────────────────────────────────────────────────────────────────────────────────────────
class DuplicateAction(str, Enum):
    """Action to take when a duplicate recipe is found during import."""
    SKIP = "skip"
    UPDATE = "update"
    RENAME = "rename"


# ── Import DTOs ─────────────────────────────────────────────────────────────────────────────────────────────
class RecipeImportRowDTO(BaseModel):
    """Single recipe row parsed from xlsx import."""

    model_config = ConfigDict(from_attributes=True)

    recipe_name: str = Field(..., min_length=1)
    recipe_category: str = Field(..., min_length=1)
    meal_type: str = Field(default="Dinner", min_length=1)
    diet_pref: Optional[str] = None
    prep_time: Optional[int] = Field(None, ge=0)
    cook_time: Optional[int] = Field(None, ge=0)
    total_time: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    directions: Optional[str] = None
    notes: Optional[str] = None
    ingredients: List[RecipeIngredientDTO] = []

    @field_validator("recipe_name", "recipe_category", "meal_type", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class DuplicateRecipeDTO(BaseModel):
    """Info about a duplicate recipe found during import."""

    model_config = ConfigDict(from_attributes=True)

    recipe_name: str
    recipe_category: str
    existing_id: int
    row_number: int


class ValidationErrorDTO(BaseModel):
    """Validation error for a specific row during import."""

    model_config = ConfigDict(from_attributes=True)

    row_number: int
    field: str
    message: str


class ImportPreviewDTO(BaseModel):
    """Preview of what will happen during import."""

    model_config = ConfigDict(from_attributes=True)

    total_recipes: int
    new_recipes: int
    duplicate_recipes: List[DuplicateRecipeDTO]
    validation_errors: List[ValidationErrorDTO]


class ImportResultDTO(BaseModel):
    """Result after import completes."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]


class DuplicateResolutionDTO(BaseModel):
    """User's choice for handling a specific duplicate recipe."""

    model_config = ConfigDict(from_attributes=True)

    recipe_name: str
    recipe_category: str
    action: DuplicateAction
    new_name: Optional[str] = None  # Required if action is RENAME

    @field_validator("new_name", mode="before")
    @classmethod
    def strip_new_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class ImportExecuteDTO(BaseModel):
    """Request to execute import with duplicate resolutions."""

    model_config = ConfigDict(from_attributes=True)

    resolutions: List[DuplicateResolutionDTO] = []


# ── Export DTOs ─────────────────────────────────────────────────────────────────────────────────────────────
class ExportFilterDTO(BaseModel):
    """Filter criteria for recipe export."""

    model_config = ConfigDict(from_attributes=True)

    recipe_category: Optional[str] = None
    meal_type: Optional[str] = None
    favorites_only: bool = False


# ── Full Backup DTOs ───────────────────────────────────────────────────────────────────────────────────────────
class IngredientBackupDTO(BaseModel):
    """Ingredient data for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_name: str
    ingredient_category: str


class RecipeBackupDTO(BaseModel):
    """Recipe data for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_name: str
    recipe_category: str
    meal_type: str
    diet_pref: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    total_time: Optional[int] = None
    servings: Optional[int] = None
    directions: Optional[str] = None
    notes: Optional[str] = None
    reference_image_path: Optional[str] = None
    banner_image_path: Optional[str] = None
    # Stable Cloudinary key; preserved on restore so image URLs keep resolving.
    # Optional for backwards compatibility with backups taken before this field.
    image_key: Optional[str] = None
    created_at: datetime
    is_favorite: bool = False


class RecipeIngredientBackupDTO(BaseModel):
    """Recipe ingredient link for full backup."""

    model_config = ConfigDict(from_attributes=True)

    recipe_id: int
    ingredient_id: int
    quantity: Optional[float] = None
    unit: Optional[str] = None


class RecipeHistoryBackupDTO(BaseModel):
    """Recipe cooking history for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    cooked_at: datetime


class MealBackupDTO(BaseModel):
    """Meal data for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_name: str
    main_recipe_id: int
    side_recipe_ids: List[int] = []
    tags: List[str] = []
    is_saved: bool = False
    created_at: datetime


class PlannerEntryBackupDTO(BaseModel):
    """Planner entry data for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_id: int
    position: int
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    scheduled_date: Optional[date] = None
    shopping_mode: str = "all"
    is_cleared: bool = False


class ShoppingItemBackupDTO(BaseModel):
    """Shopping item data for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_name: str
    quantity: float = 0.0
    unit: Optional[str] = None
    category: Optional[str] = None
    source: str
    have: bool = False
    flagged: bool = False
    state_key: Optional[str] = None
    recipe_sources: Optional[List[str]] = None


class ShoppingStateBackupDTO(BaseModel):
    """Shopping state data for full backup."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    quantity: float
    unit: str
    checked: bool = False
    flagged: bool = False


class BackupDataDTO(BaseModel):
    """Container for all backup data."""

    model_config = ConfigDict(from_attributes=True)

    ingredients: List[IngredientBackupDTO] = []
    recipes: List[RecipeBackupDTO] = []
    recipe_ingredients: List[RecipeIngredientBackupDTO] = []
    recipe_history: List[RecipeHistoryBackupDTO] = []
    meals: List[MealBackupDTO] = []
    planner_entries: List[PlannerEntryBackupDTO] = []
    shopping_items: List[ShoppingItemBackupDTO] = []
    # shopping_states kept for backwards compatibility with older backups
    # New backups will have an empty list, state is now stored on ShoppingItem
    shopping_states: List[ShoppingStateBackupDTO] = []


class FullBackupDTO(BaseModel):
    """Complete backup including settings and all data."""

    model_config = ConfigDict(from_attributes=True)

    version: str = "1.0.0"
    created_at: datetime
    # Plain str, never validated on restore — older backups tagged "meal-genie" still import
    app_name: str = "enchanted-spoon"
    settings: Optional[Dict[str, Any]] = None
    data: BackupDataDTO


class RestorePreviewDTO(BaseModel):
    """Preview of what will be restored."""

    model_config = ConfigDict(from_attributes=True)

    backup_version: str
    backup_created_at: datetime
    counts: Dict[str, int]
    has_settings: bool
    warnings: List[str] = []


class RestoreResultDTO(BaseModel):
    """Result after restore completes."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    restored_counts: Dict[str, int]
    errors: List[str] = []
    settings: Optional[Dict[str, Any]] = None
