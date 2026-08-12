"""app/core/repositories/recipes/repo.py

Repository layer for Recipe model. Handles all direct database interactions
related to recipes, including related ingredients and history.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..dtos.recipe_dtos import (
    RecipeCreateDTO,
    RecipeFilterDTO,
    RecipeIngredientDTO,
    RecipeUpdateDTO)
from ..models.nutrition_facts import NutritionFacts
from ..models.recipe import Recipe
from ..models.recipe_history import RecipeHistory
from ..models.recipe_ingredient import RecipeIngredient
from ..repositories.ingredient_repo import IngredientRepo

# Safety backstop: when a caller omits ``limit``, cap the result set instead of
# returning the user's entire table as data volumes grow.
MAX_LIST_ROWS = 1000


# ── Recipe Repository ───────────────────────────────────────────────────────────────────────────────────────
class RecipeRepo:
    """Handles direct DB queries for the Recipe model."""

    def __init__(
        self,
        session: Session,
        ingredient_repo: Optional[IngredientRepo] = None,
        user_id: Optional[int] = None
    ):
        """Initialize Recipe Repository with a database session and ingredient repository.

        Args:
            session: SQLAlchemy database session
            ingredient_repo: Optional IngredientRepo (if not provided and user_id is given,
                             creates a new user-scoped IngredientRepo)
            user_id: Optional user ID for multi-tenant ingredient operations
        """
        self.session = session
        self.user_id = user_id
        # If user_id is provided but no ingredient_repo, create a user-scoped one
        if ingredient_repo:
            self.ingredient_repo = ingredient_repo
        elif user_id:
            self.ingredient_repo = IngredientRepo(session, user_id)
        else:
            # Fallback for backward compatibility (should not be used in production)
            self.ingredient_repo = None

    def persist_recipe_and_links(self, recipe_dto: RecipeCreateDTO, user_id: int) -> Recipe:
        """
        Create a new recipe with its ingredient links.

        Args:
            recipe_dto: DTO containing recipe data and ingredients.
            user_id: ID of the user who owns this recipe.

        Returns:
            Recipe: The newly created recipe.

        Raises:
            RuntimeError: If ingredient_repo is not initialized.
        """
        if not self.ingredient_repo:
            raise RuntimeError(
                "RecipeRepo requires user_id or ingredient_repo for persist_recipe_and_links"
            )

        recipe = Recipe(
            recipe_name=recipe_dto.recipe_name,
            recipe_category=recipe_dto.recipe_category,
            meal_type=recipe_dto.meal_type,
            diet_pref=recipe_dto.diet_pref,
            description=recipe_dto.description,
            prep_time=recipe_dto.prep_time,
            cook_time=recipe_dto.cook_time,
            servings=recipe_dto.servings,
            difficulty=recipe_dto.difficulty,
            directions=recipe_dto.directions,
            notes=recipe_dto.notes,
            reference_image_path=recipe_dto.reference_image_path,
            banner_image_path=recipe_dto.banner_image_path,
            is_ai_generated=recipe_dto.is_ai_generated,
            source_url=recipe_dto.source_url,
            user_id=user_id,
        )
        self.session.add(recipe)
        # flush so recipe gets its primary key before linking ingredients
        self.session.flush()

        for ing in recipe_dto.ingredients:
            ingredient = self.ingredient_repo.get_or_create(ing)
            # flush to ensure ingredient has an ID before creating the link row
            self.session.flush()
            link = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=ing.quantity,
                unit=ing.unit
            )
            self.session.add(link)

        # Create nutrition facts if provided
        if recipe_dto.nutrition_facts:
            nf = recipe_dto.nutrition_facts
            nutrition = NutritionFacts(
                recipe_id=recipe.id,
                calories=nf.calories,
                protein_g=nf.protein_g,
                total_fat_g=nf.total_fat_g,
                saturated_fat_g=nf.saturated_fat_g,
                trans_fat_g=nf.trans_fat_g,
                cholesterol_mg=nf.cholesterol_mg,
                sodium_mg=nf.sodium_mg,
                total_carbs_g=nf.total_carbs_g,
                dietary_fiber_g=nf.dietary_fiber_g,
                total_sugars_g=nf.total_sugars_g,
                is_ai_estimated=nf.is_ai_estimated,
            )
            self.session.add(nutrition)
            self.session.flush()

        return recipe

    def get_by_id(self, recipe_id: int, user_id: Optional[int] = None) -> Optional[Recipe]:
        """
        Returns a single recipe by ID, with ingredients and history.

        Args:
            recipe_id (int): The ID of the recipe to retrieve.
            user_id (Optional[int]): If provided, only return the recipe if it belongs to this user.
                Returns None if the recipe exists but belongs to a different user (no existence leak).

        Returns:
            Optional[Recipe]: The recipe with the given ID, or None if not found/not owned.
        """
        stmt = (
            select(Recipe)
            .options(
                joinedload(Recipe.ingredients),
                joinedload(Recipe.history),
                joinedload(Recipe.nutrition_facts),
            )
            .where(Recipe.id == recipe_id)
        )
        if user_id is not None:
            stmt = stmt.where(Recipe.user_id == user_id)
        return self.session.scalars(stmt).unique().first()

    def get_last_cooked_date(self, recipe_id: int, user_id: int) -> Optional[datetime]:
        """
        Returns the most recent cooked_at datetime for a recipe.

        Args:
            recipe_id (int): The ID of the recipe to check.
            user_id (int): The ID of the user who owns the recipe.

        Returns:
            Optional[datetime]: The last cooked date, or None if no history exists or recipe not owned.
        """
        stmt = (
            select(RecipeHistory.cooked_at)
            .join(Recipe, Recipe.id == RecipeHistory.recipe_id)
            .where(RecipeHistory.recipe_id == recipe_id)
            .where(Recipe.user_id == user_id)
            .order_by(RecipeHistory.cooked_at.desc())
            .limit(1)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result

    def record_cooked(self, recipe_id: int, user_id: int) -> Optional[RecipeHistory]:
        """
        Record that a recipe was cooked by creating a RecipeHistory entry.

        Args:
            recipe_id (int): The ID of the recipe that was cooked.
            user_id (int): The ID of the user who owns the recipe.

        Returns:
            Optional[RecipeHistory]: The created history record, or None if recipe not found/owned.
        """
        # Verify ownership before creating history
        recipe = self.get_by_id(recipe_id, user_id)
        if not recipe:
            return None
        history = RecipeHistory(recipe_id=recipe_id, user_id=user_id)
        self.session.add(history)
        self.session.flush()
        return history

    def get_times_cooked(self, recipe_id: int, user_id: int) -> int:
        """
        Returns the number of times a recipe has been cooked.

        Args:
            recipe_id (int): The ID of the recipe to check.
            user_id (int): The ID of the user who owns the recipe.

        Returns:
            int: The count of cooking history records (0 if recipe not owned).
        """
        stmt = (
            select(func.count())
            .select_from(RecipeHistory)
            .join(Recipe, Recipe.id == RecipeHistory.recipe_id)
            .where(RecipeHistory.recipe_id == recipe_id)
            .where(Recipe.user_id == user_id)
        )
        return self.session.execute(stmt).scalar() or 0

    def update_recipe(self, recipe_id: int, update_dto: RecipeUpdateDTO, user_id: int) -> Optional[Recipe]:
        """
        Update a recipe's core fields and replace ingredient links.

        Args:
            recipe_id (int): The ID of the recipe to update.
            update_dto (RecipeUpdateDTO): DTO containing updated recipe data.
            user_id (int): The ID of the user who owns the recipe.

        Returns:
            Optional[Recipe]: The updated recipe, or None if not found/not owned.
        """
        recipe = self.get_by_id(recipe_id, user_id)
        if not recipe:
            return None

        update_data = update_dto.model_dump(exclude_unset=True)

        for field in [
            "recipe_name",
            "recipe_category",
            "meal_type",
            "diet_pref",
            "description",
            "prep_time",
            "cook_time",
            "servings",
            "difficulty",
            "directions",
            "notes",
            "reference_image_path",
            "banner_image_path",
            "is_favorite",
        ]:
            if field in update_data:
                setattr(recipe, field, update_data[field])

        if "ingredients" in update_data and update_data["ingredients"] is not None:
            if not self.ingredient_repo:
                raise RuntimeError(
                    "RecipeRepo requires user_id or ingredient_repo for updating ingredients"
                )
            recipe.ingredients.clear()
            # flush to persist removal of old links before adding replacements
            self.session.flush()
            for ing in update_data["ingredients"]:
                ing_dto = (
                    RecipeIngredientDTO(**ing)
                    if isinstance(ing, dict)
                    else ing
                )
                ingredient = self.ingredient_repo.get_or_create(ing_dto)
                # flush so ingredient has an ID before we append the new link
                self.session.flush()
                recipe.ingredients.append(
                    RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=ing_dto.quantity,
                        unit=ing_dto.unit,
                    )
                )

        # Handle nutrition_facts update
        if "nutrition_facts" in update_data:
            nf_data = update_data["nutrition_facts"]
            if nf_data is None:
                # Explicitly set to None — delete existing nutrition
                if recipe.nutrition_facts:
                    self.session.delete(recipe.nutrition_facts)
                    self.session.flush()
            else:
                from ..dtos.nutrition_dtos import NutritionFactsDTO
                nf_dto = (
                    NutritionFactsDTO(**nf_data)
                    if isinstance(nf_data, dict)
                    else nf_data
                )
                if recipe.nutrition_facts:
                    recipe.nutrition_facts.calories = nf_dto.calories
                    recipe.nutrition_facts.protein_g = nf_dto.protein_g
                    recipe.nutrition_facts.total_fat_g = nf_dto.total_fat_g
                    recipe.nutrition_facts.saturated_fat_g = nf_dto.saturated_fat_g
                    recipe.nutrition_facts.trans_fat_g = nf_dto.trans_fat_g
                    recipe.nutrition_facts.cholesterol_mg = nf_dto.cholesterol_mg
                    recipe.nutrition_facts.sodium_mg = nf_dto.sodium_mg
                    recipe.nutrition_facts.total_carbs_g = nf_dto.total_carbs_g
                    recipe.nutrition_facts.dietary_fiber_g = nf_dto.dietary_fiber_g
                    recipe.nutrition_facts.total_sugars_g = nf_dto.total_sugars_g
                    recipe.nutrition_facts.is_ai_estimated = nf_dto.is_ai_estimated
                else:
                    nutrition = NutritionFacts(
                        recipe_id=recipe.id,
                        calories=nf_dto.calories,
                        protein_g=nf_dto.protein_g,
                        total_fat_g=nf_dto.total_fat_g,
                        saturated_fat_g=nf_dto.saturated_fat_g,
                        trans_fat_g=nf_dto.trans_fat_g,
                        cholesterol_mg=nf_dto.cholesterol_mg,
                        sodium_mg=nf_dto.sodium_mg,
                        total_carbs_g=nf_dto.total_carbs_g,
                        dietary_fiber_g=nf_dto.dietary_fiber_g,
                        total_sugars_g=nf_dto.total_sugars_g,
                        is_ai_estimated=nf_dto.is_ai_estimated,
                    )
                    self.session.add(nutrition)
                self.session.flush()

        return recipe

    def create_recipe(self, recipe: Recipe) -> Recipe:
        """
        Adds and returns a new recipe.

        Args:
            recipe (Recipe): The recipe instance to add.

        Returns:
            Recipe: The newly created recipe with ID and other defaults set.
        """
        self.session.add(recipe)
        self.session.refresh(recipe)
        return recipe

    def delete_recipe(self, recipe: Recipe) -> None:
        """
        Delete the given recipe.

        Args:
            recipe (Recipe): The recipe instance to delete.

        Note:
            Related data is handled by database foreign key rules:
            - Recipe ingredients and history: CASCADE (deleted)
            - Meal selections (main recipe): CASCADE (deleted)
            - Meal selections (side recipe): SET NULL
        """
        self.session.delete(recipe)

    def recipe_exists(self, name: str, category: str, user_id: int) -> bool:
        """
        Check if a user already has a recipe with the same name and category (case-insensitive).

        Args:
            name (str): The name of the recipe.
            category (str): The category of the recipe.
            user_id (int): The ID of the user to check recipes for.

        Returns:
            bool: True if the user has a recipe with the same name and category, False otherwise.
        """
        return (
            self.session.query(Recipe)
            .filter(
                func.lower(Recipe.recipe_name) == name.strip().lower(),
                func.lower(Recipe.recipe_category) == category.strip().lower(),
                Recipe.user_id == user_id,
            )
            .first()
            is not None
        )

    def filter_recipes(self, filter_dto: RecipeFilterDTO, user_id: int) -> list[Recipe]:
        """
        Filter and sort recipes based on various criteria.

        Args:
            filter_dto (RecipeFilterDTO): DTO containing filter, sort, and pagination criteria.
            user_id (int): The ID of the user whose recipes to filter.

        Returns:
            List[Recipe]: A list of recipes that match the specified criteria.
        """
        # Start with a base query to select recipes and eager-load everything the
        # response DTO touches (groups and nutrition_facts would otherwise lazy-load
        # per recipe — an N+1 that is painful over a networked database)
        stmt = select(Recipe).options(
            joinedload(Recipe.ingredients),
            selectinload(Recipe.groups),
            selectinload(Recipe.nutrition_facts),
        )

        # Always filter by user - users only see their own recipes
        stmt = stmt.where(Recipe.user_id == user_id)

        # Apply filters based on the DTO
        if filter_dto.recipe_category and filter_dto.recipe_category not in ["All", "Filter"]:
            stmt = stmt.where(Recipe.recipe_category == filter_dto.recipe_category)

        if filter_dto.favorites_only:
            stmt = stmt.where(Recipe.is_favorite == True)

        if filter_dto.search_term:
            # Use ilike for case-insensitive search
            search_pattern = f"%{filter_dto.search_term}%"
            stmt = stmt.where(Recipe.recipe_name.ilike(search_pattern))

        # Apply sorting
        if filter_dto.sort_by:
            sort_column = getattr(Recipe, filter_dto.sort_by, None)
            if sort_column:
                if filter_dto.sort_order == 'desc':
                    stmt = stmt.order_by(sort_column.desc())
                else:
                    stmt = stmt.order_by(sort_column.asc())

        # Apply pagination. Cap results when no explicit limit is given so an
        # omitted limit can't return the user's entire table.
        if filter_dto.offset:
            stmt = stmt.offset(filter_dto.offset)

        stmt = stmt.limit(filter_dto.limit or MAX_LIST_ROWS)

        # Execute the query and return the results
        result = self.session.scalars(stmt).unique().all()
        return result

    def toggle_favorite(self, recipe_id: int, user_id: int) -> Optional[Recipe]:
        """
        Toggle the favorite status of a recipe.

        Args:
            recipe_id (int): ID of the recipe to toggle.
            user_id (int): ID of the user who owns the recipe.

        Returns:
            Optional[Recipe]: The updated recipe with new favorite status, or None if not found/owned.
        """
        recipe = self.get_by_id(recipe_id, user_id)
        if recipe is None:
            return None
        recipe.is_favorite = not recipe.is_favorite
        return recipe
