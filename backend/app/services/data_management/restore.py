"""app/services/data_management/restore.py

Restore operations mixin for data management service.
Handles restore preview and full restore execution.
"""

# -- Imports -------------------------------------------------------------------------------------
from typing import Dict, List

from ...dtos.data_management_dtos import (
    FullBackupDTO,
    RestorePreviewDTO,
    RestoreResultDTO,
)
from ...models import (
    Ingredient,
    Meal,
    PlannerEntry,
    Recipe,
    RecipeHistory,
    RecipeIngredient,
    ShoppingItem,
)


# -- Restore Operations Mixin --------------------------------------------------------------------
class RestoreOperationsMixin:
    """Mixin providing restore operations (preview, execute)."""

    # -- Preview Restore -------------------------------------------------------------------------
    def preview_restore(self, backup: FullBackupDTO) -> RestorePreviewDTO:
        """
        Preview what will be restored without making changes.

        Args:
            backup: The backup data to preview.

        Returns:
            RestorePreviewDTO with counts and warnings.
        """
        counts = {
            "ingredients": len(backup.data.ingredients),
            "recipes": len(backup.data.recipes),
            "recipe_ingredients": len(backup.data.recipe_ingredients),
            "recipe_history": len(backup.data.recipe_history),
            "meals": len(backup.data.meals),
            "planner_entries": len(backup.data.planner_entries),
            "shopping_items": len(backup.data.shopping_items),
        }

        warnings: List[str] = []

        # Check version compatibility
        if backup.version != "1.0.0":
            warnings.append(f"Backup version {backup.version} may not be fully compatible")

        # Check for existing data
        existing_recipes = (
            self.session.query(Recipe).filter(Recipe.user_id == self._require_user_id()).count()
        )
        if existing_recipes > 0:
            warnings.append(f"Existing data ({existing_recipes} recipes) will be deleted before restore")

        return RestorePreviewDTO(
            backup_version=backup.version,
            backup_created_at=backup.created_at,
            counts=counts,
            has_settings=backup.settings is not None,
            warnings=warnings,
        )

    # -- Execute Restore -------------------------------------------------------------------------
    def execute_restore(
        self, backup: FullBackupDTO, clear_existing: bool = True
    ) -> RestoreResultDTO:
        """
        Execute a full restore from backup.

        Restores data in dependency order to maintain referential integrity:
        1. Ingredients (no dependencies)
        2. Recipes (no dependencies)
        3. Recipe Ingredients (depends on recipes + ingredients)
        4. Recipe History (depends on recipes)
        5. Meals (depends on recipes)
        6. Planner Entries (depends on meals)
        7. Shopping States (no dependencies)
        8. Shopping Items (no dependencies)

        Args:
            backup: The backup data to restore.
            clear_existing: If True, clear all existing data first.

        Returns:
            RestoreResultDTO with counts and any errors.
        """
        user_id = self._require_user_id()
        errors: List[str] = []
        restored_counts: Dict[str, int] = {}

        try:
            if clear_existing:
                # Keep the Cloudinary images: the backup points at them
                self.clear_all_data(delete_images=False)

            # Build ID mappings as we restore (old_id -> new_id)
            ingredient_id_map: Dict[int, int] = {}
            recipe_id_map: Dict[int, int] = {}
            meal_id_map: Dict[int, int] = {}

            # 1. Restore ingredients
            for ing_dto in backup.data.ingredients:
                new_ing = Ingredient(
                    ingredient_name=ing_dto.ingredient_name,
                    ingredient_category=ing_dto.ingredient_category,
                    user_id=user_id,
                )
                self.session.add(new_ing)
                self.session.flush()
                ingredient_id_map[ing_dto.id] = new_ing.id
            restored_counts["ingredients"] = len(backup.data.ingredients)

            # 2. Restore recipes
            for recipe_dto in backup.data.recipes:
                cook_time = recipe_dto.cook_time
                if cook_time is None and recipe_dto.total_time is not None:
                    cook_time = recipe_dto.total_time
                new_recipe = Recipe(
                    recipe_name=recipe_dto.recipe_name,
                    recipe_category=recipe_dto.recipe_category,
                    meal_type=recipe_dto.meal_type,
                    diet_pref=recipe_dto.diet_pref,
                    prep_time=recipe_dto.prep_time,
                    cook_time=cook_time,
                    servings=recipe_dto.servings,
                    directions=recipe_dto.directions,
                    notes=recipe_dto.notes,
                    reference_image_path=recipe_dto.reference_image_path,
                    banner_image_path=recipe_dto.banner_image_path,
                    created_at=recipe_dto.created_at,
                    is_favorite=recipe_dto.is_favorite,
                    user_id=user_id,
                )
                # Preserve the stable image_key so restored recipes keep pointing
                # at their own Cloudinary assets. Older backups without an
                # image_key, or whose key another recipe already holds, fall back
                # to the model-generated default so they never write to that
                # recipe's asset.
                if recipe_dto.image_key and not self._image_key_in_use(recipe_dto.image_key):
                    new_recipe.image_key = recipe_dto.image_key
                self.session.add(new_recipe)
                self.session.flush()
                recipe_id_map[recipe_dto.id] = new_recipe.id
            restored_counts["recipes"] = len(backup.data.recipes)

            # 3. Restore recipe ingredients (using mapped IDs)
            for ri_dto in backup.data.recipe_ingredients:
                new_recipe_id = recipe_id_map.get(ri_dto.recipe_id)
                new_ingredient_id = ingredient_id_map.get(ri_dto.ingredient_id)
                if new_recipe_id and new_ingredient_id:
                    new_ri = RecipeIngredient(
                        recipe_id=new_recipe_id,
                        ingredient_id=new_ingredient_id,
                        quantity=ri_dto.quantity,
                        unit=ri_dto.unit,
                    )
                    self.session.add(new_ri)
                else:
                    errors.append(f"Skipped recipe ingredient: missing recipe or ingredient reference")
            restored_counts["recipe_ingredients"] = len(backup.data.recipe_ingredients)

            # 4. Restore recipe history (using mapped recipe IDs)
            for rh_dto in backup.data.recipe_history:
                new_recipe_id = recipe_id_map.get(rh_dto.recipe_id)
                if new_recipe_id:
                    new_rh = RecipeHistory(
                        recipe_id=new_recipe_id,
                        cooked_at=rh_dto.cooked_at,
                        user_id=user_id,
                    )
                    self.session.add(new_rh)
                else:
                    errors.append(f"Skipped recipe history: missing recipe reference")
            restored_counts["recipe_history"] = len(backup.data.recipe_history)

            # 5. Restore meals (using mapped recipe IDs)
            for meal_dto in backup.data.meals:
                new_main_recipe_id = recipe_id_map.get(meal_dto.main_recipe_id)
                if new_main_recipe_id:
                    new_side_ids = [
                        recipe_id_map.get(sid)
                        for sid in meal_dto.side_recipe_ids
                        if recipe_id_map.get(sid)
                    ]
                    new_meal = Meal(
                        meal_name=meal_dto.meal_name,
                        main_recipe_id=new_main_recipe_id,
                        is_saved=meal_dto.is_saved,
                        created_at=meal_dto.created_at,
                        user_id=user_id,
                    )
                    new_meal.side_recipe_ids = new_side_ids
                    new_meal.tags = meal_dto.tags
                    self.session.add(new_meal)
                    self.session.flush()
                    meal_id_map[meal_dto.id] = new_meal.id
                else:
                    errors.append(f"Skipped meal '{meal_dto.meal_name}': missing main recipe reference")
            restored_counts["meals"] = len(backup.data.meals)

            # 6. Restore planner entries (using mapped meal IDs)
            for pe_dto in backup.data.planner_entries:
                new_meal_id = meal_id_map.get(pe_dto.meal_id)
                if new_meal_id:
                    new_pe = PlannerEntry(
                        meal_id=new_meal_id,
                        position=pe_dto.position,
                        is_completed=pe_dto.is_completed,
                        completed_at=pe_dto.completed_at,
                        scheduled_date=pe_dto.scheduled_date,
                        shopping_mode=pe_dto.shopping_mode,
                        is_cleared=pe_dto.is_cleared,
                        user_id=user_id,
                    )
                    self.session.add(new_pe)
                else:
                    errors.append(f"Skipped planner entry: missing meal reference")
            restored_counts["planner_entries"] = len(backup.data.planner_entries)

            # 7. Restore shopping items (only manual items - recipe items will be regenerated by sync)
            manual_items_count = 0
            for si_dto in backup.data.shopping_items:
                if si_dto.source == "manual":
                    new_si = ShoppingItem(
                        ingredient_name=si_dto.ingredient_name,
                        quantity=si_dto.quantity,
                        unit=si_dto.unit,
                        category=si_dto.category,
                        source=si_dto.source,
                        have=si_dto.have,
                        flagged=si_dto.flagged,
                        user_id=user_id,
                    )
                    self.session.add(new_si)
                    manual_items_count += 1
            restored_counts["shopping_items"] = manual_items_count

            self.session.commit()

            # 8. Sync shopping list to regenerate recipe items from planner
            from ..shopping import ShoppingService
            shopping_service = ShoppingService(self.session, self.user_id)
            shopping_service.sync_shopping_list()

        except Exception as e:
            self.session.rollback()
            return RestoreResultDTO(
                success=False,
                restored_counts={},
                errors=[f"Database error: {str(e)}"],
                settings=backup.settings,
            )

        return RestoreResultDTO(
            success=len(errors) == 0,
            restored_counts=restored_counts,
            errors=errors,
            settings=backup.settings,
        )

    def _image_key_in_use(self, image_key: str) -> bool:
        """Whether any recipe (in any account) already holds this image_key."""
        return (
            self.session.query(Recipe.id).filter(Recipe.image_key == image_key).first()
            is not None
        )
