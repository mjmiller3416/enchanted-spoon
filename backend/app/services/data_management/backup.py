"""app/services/data_management/backup.py

Backup operations mixin for data management service.
Handles full backup export, data clearing, and Cloudinary image cleanup.
"""

# -- Imports -------------------------------------------------------------------------------------
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

import cloudinary.uploader

from ...dtos.data_management_dtos import (
    BackupDataDTO,
    FullBackupDTO,
    IngredientBackupDTO,
    MealBackupDTO,
    PlannerEntryBackupDTO,
    RecipeBackupDTO,
    RecipeHistoryBackupDTO,
    RecipeIngredientBackupDTO,
    ShoppingItemBackupDTO,
)
from ...models import (
    Ingredient,
    Meal,
    PlannerEntry,
    Recipe,
    RecipeHistory,
    RecipeIngredient,
    ShoppingItem,
    ShoppingItemContribution,
)
from ..sample_data.starter_pack import starter_image_urls


# -- Backup Operations Mixin ---------------------------------------------------------------------
class BackupOperationsMixin:
    """Mixin providing backup and data clearing operations."""

    # -- Cloudinary Cleanup ----------------------------------------------------------------------
    def _extract_cloudinary_public_id(self, url: str) -> Optional[str]:
        """
        Extract the public_id from a Cloudinary URL.

        Cloudinary URLs look like:
        https://res.cloudinary.com/{cloud}/image/upload/v{version}/{public_id}.{ext}

        Returns the public_id without the file extension.
        """
        if not url:
            return None

        # Match the path after /upload/ and before the file extension
        # Example: .../upload/v1234567890/meal-genie/recipes/123/reference_123.jpg
        match = re.search(r"/upload/(?:v\d+/)?(.+)\.\w+$", url)
        if match:
            return match.group(1)
        return None

    def _delete_cloudinary_images(self, recipes: List[Recipe]) -> int:
        """
        Delete all Cloudinary images for the given recipes.

        Returns the count of successfully deleted images.
        """
        # Starter-pack artwork is shared by every account; never destroy it
        shared = starter_image_urls()
        deleted_count = 0

        for recipe in recipes:
            for image_path in [recipe.reference_image_path, recipe.banner_image_path]:
                if image_path and image_path not in shared:
                    public_id = self._extract_cloudinary_public_id(image_path)
                    if public_id:
                        try:
                            result = cloudinary.uploader.destroy(public_id)
                            if result.get("result") == "ok":
                                deleted_count += 1
                        except Exception:
                            # Continue even if individual deletion fails
                            pass

        return deleted_count

    # -- Clear All Data --------------------------------------------------------------------------
    def clear_all_data(self) -> Dict[str, int]:
        """
        Delete all data from all tables, including Cloudinary images.

        Deletes Cloudinary images first, then tables in the correct order
        to respect foreign key constraints.

        Returns:
            Dict with counts of deleted records per table.
        """
        counts = {}

        # First, delete Cloudinary images before removing recipe records
        recipes_with_images = (
            self.session.query(Recipe)
            .filter(
                (Recipe.reference_image_path.isnot(None))
                | (Recipe.banner_image_path.isnot(None))
            )
            .all()
        )
        counts["cloudinary_images"] = self._delete_cloudinary_images(recipes_with_images)

        # Delete in order to respect foreign key constraints
        # Shopping contributions depend on ShoppingItem
        counts["shopping_contributions"] = self.session.query(ShoppingItemContribution).delete()

        # Shopping items
        counts["shopping_items"] = self.session.query(ShoppingItem).delete()

        # Planner entries depend on Recipe
        counts["planner_entries"] = self.session.query(PlannerEntry).delete()

        # Recipe ingredients depend on Recipe and Ingredient
        counts["recipe_ingredients"] = self.session.query(RecipeIngredient).delete()

        # Recipe history depends on Recipe
        counts["recipe_history"] = self.session.query(RecipeHistory).delete()

        # Recipes
        counts["recipes"] = self.session.query(Recipe).delete()

        # Meals
        counts["meals"] = self.session.query(Meal).delete()

        # Ingredients (can be deleted after recipe_ingredients)
        counts["ingredients"] = self.session.query(Ingredient).delete()

        self.session.commit()

        return counts

    # -- Full Backup Export ----------------------------------------------------------------------
    def export_full_backup(self) -> FullBackupDTO:
        """
        Export all database data as a FullBackupDTO.

        Settings are not included here (they come from frontend localStorage).

        Returns:
            FullBackupDTO with all database data.
        """
        # Query all tables
        ingredients = self.session.query(Ingredient).all()
        recipes = self.session.query(Recipe).all()
        recipe_ingredients = self.session.query(RecipeIngredient).all()
        recipe_history = self.session.query(RecipeHistory).all()
        meals = self.session.query(Meal).all()
        planner_entries = self.session.query(PlannerEntry).all()
        shopping_items = self.session.query(ShoppingItem).all()

        # Convert to DTOs
        return FullBackupDTO(
            created_at=datetime.now(timezone.utc),
            data=BackupDataDTO(
                ingredients=[
                    IngredientBackupDTO(
                        id=ing.id,
                        ingredient_name=ing.ingredient_name,
                        ingredient_category=ing.ingredient_category,
                    )
                    for ing in ingredients
                ],
                recipes=[
                    RecipeBackupDTO(
                        id=r.id,
                        recipe_name=r.recipe_name,
                        recipe_category=r.recipe_category,
                        meal_type=r.meal_type,
                        diet_pref=r.diet_pref,
                        prep_time=r.prep_time,
                        cook_time=r.cook_time,
                        servings=r.servings,
                        directions=r.directions,
                        notes=r.notes,
                        reference_image_path=r.reference_image_path,
                        banner_image_path=r.banner_image_path,
                        image_key=r.image_key,
                        created_at=r.created_at,
                        is_favorite=r.is_favorite,
                    )
                    for r in recipes
                ],
                recipe_ingredients=[
                    RecipeIngredientBackupDTO(
                        recipe_id=ri.recipe_id,
                        ingredient_id=ri.ingredient_id,
                        quantity=ri.quantity,
                        unit=ri.unit,
                    )
                    for ri in recipe_ingredients
                ],
                recipe_history=[
                    RecipeHistoryBackupDTO(
                        id=rh.id,
                        recipe_id=rh.recipe_id,
                        cooked_at=rh.cooked_at,
                    )
                    for rh in recipe_history
                ],
                meals=[
                    MealBackupDTO(
                        id=m.id,
                        meal_name=m.meal_name,
                        main_recipe_id=m.main_recipe_id,
                        side_recipe_ids=m.side_recipe_ids,
                        tags=m.tags,
                        is_saved=m.is_saved,
                        created_at=m.created_at,
                    )
                    for m in meals
                ],
                planner_entries=[
                    PlannerEntryBackupDTO(
                        id=pe.id,
                        meal_id=pe.meal_id,
                        position=pe.position,
                        is_completed=pe.is_completed,
                        completed_at=pe.completed_at,
                        scheduled_date=pe.scheduled_date,
                        shopping_mode=pe.shopping_mode,
                        is_cleared=pe.is_cleared,
                    )
                    for pe in planner_entries
                ],
                shopping_items=[
                    ShoppingItemBackupDTO(
                        id=si.id,
                        ingredient_name=si.ingredient_name,
                        quantity=si.quantity,
                        unit=si.unit,
                        category=si.category,
                        source=si.source,
                        have=si.have,
                        flagged=si.flagged,
                        state_key=si.aggregation_key,  # Use aggregation_key for backwards compat
                        recipe_sources=[],  # Contributions are rebuilt on restore via sync
                    )
                    for si in shopping_items
                ],
                # shopping_states removed - state now lives on ShoppingItem directly
                shopping_states=[],
            ),
        )
