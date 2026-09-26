"""app/services/data_management/service.py

Core data management service with initialization and shared helpers.
"""

# -- Imports -------------------------------------------------------------------------------------
import os
from typing import Dict, List, Optional

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables for Cloudinary config
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

from ...repositories.ingredient_repo import IngredientRepo
from ...repositories.recipe_repo import RecipeRepo


# -- Constants -----------------------------------------------------------------------------------
RECIPE_COLUMNS = [
    "recipe_name",
    "recipe_category",
    "meal_type",
    "diet_pref",
    "prep_time",
    "cook_time",
    "servings",
    "directions",
    "notes",
]

INGREDIENT_COLUMNS = [
    "recipe_name",
    "recipe_category",
    "ingredient_name",
    "ingredient_category",
    "quantity",
    "unit",
]


# -- Core Service --------------------------------------------------------------------------------
class DataManagementServiceCore:
    """Core data management service with initialization and shared helpers."""

    def __init__(self, session: Session, user_id: int = None):
        """Initialize the service with a database session and optional user ID.

        Args:
            session: SQLAlchemy database session
            user_id: ID of the current user for multi-tenant operations (required for write operations)
        """
        self.session = session
        self.user_id = user_id
        # Ingredient repo requires user_id for user-scoped operations
        # For read-only operations (template generation), user_id can be None
        if user_id:
            self.ingredient_repo = IngredientRepo(session, user_id)
            self.recipe_repo = RecipeRepo(session, self.ingredient_repo, user_id)
        else:
            self.ingredient_repo = None
            self.recipe_repo = RecipeRepo(session, user_id=None)

    # -- Shared Helper Methods -------------------------------------------------------------------
    def _require_user_id(self) -> int:
        """Return the owning user's ID, refusing to run tenant data operations without one.

        Every read, clear, and restore must be scoped to a single account; an
        unscoped query here would reach every user's data.
        """
        if not self.user_id:
            raise ValueError("DataManagementService requires a user_id for data operations")
        return self.user_id

    def _get_cell_value(self, cells: List, col_map: Dict[str, int], column: str):
        """Get cell value by column name, returns None if column doesn't exist."""
        if column not in col_map:
            return None
        idx = col_map[column]
        if idx >= len(cells):
            return None
        value = cells[idx]
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

    def _parse_int(self, value) -> Optional[int]:
        """Parse a value to int, returns None if invalid."""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _parse_float(self, value) -> Optional[float]:
        """Parse a value to float, returns None if invalid."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
