"""app/services/user_ingredient_category_service.py

Service layer for managing user ingredient category CRUD operations.
Orchestrates repository operations and business logic for user ingredient categories.
Includes auto-seeding of built-in ingredient categories on first access.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

import re
from typing import List

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session

from ..dtos.user_ingredient_category_dtos import (
    UserIngredientCategoryBulkUpdateDTO,
    UserIngredientCategoryCreateDTO,
    UserIngredientCategoryReorderDTO,
    UserIngredientCategoryResponseDTO,
    UserIngredientCategoryUpdateDTO,
)
from ..repositories.user_ingredient_category_repo import UserIngredientCategoryRepo


# -- Constants -----------------------------------------------------------------------------------
BUILT_IN_INGREDIENT_CATEGORIES = [
    {"value": "produce", "label": "Produce"},
    {"value": "dairy", "label": "Dairy"},
    {"value": "deli", "label": "Deli"},
    {"value": "meat", "label": "Meat"},
    {"value": "condiments", "label": "Condiments"},
    {"value": "oils-and-vinegars", "label": "Oils and Vinegars"},
    {"value": "seafood", "label": "Seafood"},
    {"value": "pantry", "label": "Pantry"},
    {"value": "spices", "label": "Spices"},
    {"value": "frozen", "label": "Frozen"},
    {"value": "bakery", "label": "Bakery"},
    {"value": "baking", "label": "Baking"},
    {"value": "beverages", "label": "Beverages"},
    {"value": "other", "label": "Other"},
]

MAX_CUSTOM_CATEGORIES = 50


# -- Exceptions ----------------------------------------------------------------------------------
class UserIngredientCategoryNotFoundError(Exception):
    """Raised when a user ingredient category is not found."""

    pass


class DuplicateUserIngredientCategoryError(Exception):
    """Raised when attempting to create an ingredient category with a duplicate slug."""

    pass


class UserIngredientCategorySaveError(Exception):
    """Raised when a user ingredient category cannot be saved."""

    pass


class BuiltInIngredientCategoryError(Exception):
    """Raised when attempting to delete or rename a built-in ingredient category."""

    pass


class IngredientCategoryLimitExceededError(Exception):
    """Raised when user has reached the maximum number of custom ingredient categories."""

    pass


# -- UserIngredientCategory Service --------------------------------------------------------------
class UserIngredientCategoryService:
    """Service for user ingredient category operations with business logic."""

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the UserIngredientCategoryService with a database session and user ID.

        Args:
            session: SQLAlchemy database session (required).
            user_id: ID of the authenticated user (required for multi-tenant isolation).
        """
        self.session = session
        self.user_id = user_id
        self.repo = UserIngredientCategoryRepo(self.session)

    # -- Private Helpers -------------------------------------------------------------------------
    def _ensure_categories_exist(self) -> None:
        """
        Ensure the user has ingredient categories seeded.

        If the user has no ingredient categories, seed the built-in defaults.
        This is called at the start of operations to ensure auto-seeding.
        """
        count = self.repo.count(self.user_id)
        if count == 0:
            self.repo.seed_defaults(self.user_id, BUILT_IN_INGREDIENT_CATEGORIES)
            # Commit (not just flush): a read-only GET would otherwise roll the
            # seed back and hand out ids that never existed
            try:
                self.session.commit()
            except IntegrityError:
                # A concurrent request seeded first; use its rows
                self.session.rollback()

    def _generate_slug(self, label: str) -> str:
        """
        Generate a URL-safe slug from a label.

        Args:
            label: Display label to convert

        Returns:
            Lowercase, hyphenated slug
        """
        # Convert to lowercase
        slug = label.lower()
        # Replace spaces with hyphens
        slug = slug.replace(" ", "-")
        # Remove special characters (keep only alphanumeric and hyphens)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        # Remove consecutive hyphens
        slug = re.sub(r"-+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        return slug

    def _ensure_unique_slug(self, base_slug: str) -> str:
        """
        Ensure a slug is unique by appending a number if necessary.

        Args:
            base_slug: The base slug to check

        Returns:
            A unique slug
        """
        slug = base_slug
        counter = 1

        while self.repo.get_by_value(slug, self.user_id):
            counter += 1
            slug = f"{base_slug}-{counter}"

        return slug

    # -- Create Operations -----------------------------------------------------------------------
    def create_category(self, create_dto: UserIngredientCategoryCreateDTO) -> UserIngredientCategoryResponseDTO:
        """
        Create a new custom ingredient category for the current user.

        Args:
            create_dto: Data for creating the ingredient category

        Returns:
            Created ingredient category as DTO

        Raises:
            IngredientCategoryLimitExceededError: If user has reached max custom categories
            DuplicateUserIngredientCategoryError: If a category with this slug already exists
            UserIngredientCategorySaveError: If the category cannot be saved
        """
        try:
            self._ensure_categories_exist()

            # Check custom category limit
            custom_count = self.repo.count_custom(self.user_id)
            if custom_count >= MAX_CUSTOM_CATEGORIES:
                raise IngredientCategoryLimitExceededError(
                    f"Maximum {MAX_CUSTOM_CATEGORIES} custom ingredient categories allowed"
                )

            # Generate slug from label
            base_slug = self._generate_slug(create_dto.label)
            if not base_slug:
                raise UserIngredientCategorySaveError("Could not generate a valid slug from the label")

            slug = self._ensure_unique_slug(base_slug)

            # Get next position
            max_position = self.repo.get_max_position(self.user_id)
            new_position = max_position + 1

            # Create the category
            category = self.repo.create(
                user_id=self.user_id,
                value=slug,
                label=create_dto.label,
                is_custom=True,
                position=new_position,
            )
            self.session.commit()

            return UserIngredientCategoryResponseDTO.from_model(category)

        except (IngredientCategoryLimitExceededError, DuplicateUserIngredientCategoryError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientCategorySaveError(f"Failed to create ingredient category: {str(e)}")

    # -- Read Operations -------------------------------------------------------------------------
    def get_all_categories(
        self, include_disabled: bool = False
    ) -> List[UserIngredientCategoryResponseDTO]:
        """
        Get all ingredient categories for the current user.

        Args:
            include_disabled: If True, include disabled categories

        Returns:
            List of all ingredient categories belonging to the user
        """
        self._ensure_categories_exist()

        categories = self.repo.get_all(self.user_id, include_disabled=include_disabled)
        return [UserIngredientCategoryResponseDTO.from_model(cat) for cat in categories]

    def get_category_by_id(self, category_id: int) -> UserIngredientCategoryResponseDTO:
        """
        Get an ingredient category by ID.

        Args:
            category_id: ID of the ingredient category to retrieve

        Returns:
            Ingredient category as DTO

        Raises:
            UserIngredientCategoryNotFoundError: If category not found or not owned by user
        """
        self._ensure_categories_exist()

        category = self.repo.get_by_id(category_id, self.user_id)
        if not category:
            raise UserIngredientCategoryNotFoundError(f"Ingredient category {category_id} not found")

        return UserIngredientCategoryResponseDTO.from_model(category)

    # -- Update Operations -----------------------------------------------------------------------
    def update_category(
        self, category_id: int, update_dto: UserIngredientCategoryUpdateDTO
    ) -> UserIngredientCategoryResponseDTO:
        """
        Update an ingredient category.

        Args:
            category_id: ID of the ingredient category to update
            update_dto: Data for updating the ingredient category

        Returns:
            Updated ingredient category as DTO

        Raises:
            UserIngredientCategoryNotFoundError: If category not found or not owned by user
            BuiltInIngredientCategoryError: If trying to rename a built-in category
            UserIngredientCategorySaveError: If the category cannot be updated
        """
        try:
            self._ensure_categories_exist()

            # Check if category exists
            category = self.repo.get_by_id(category_id, self.user_id)
            if not category:
                raise UserIngredientCategoryNotFoundError(f"Ingredient category {category_id} not found")

            # Cannot rename built-in categories
            if update_dto.label is not None and not category.is_custom:
                raise BuiltInIngredientCategoryError(
                    "Cannot rename built-in ingredient categories. You can only enable/disable them."
                )

            # Update the category
            updated_category = self.repo.update(
                category_id=category_id,
                user_id=self.user_id,
                label=update_dto.label,
                is_enabled=update_dto.is_enabled,
            )
            self.session.commit()

            if not updated_category:
                raise UserIngredientCategoryNotFoundError(f"Ingredient category {category_id} not found")

            return UserIngredientCategoryResponseDTO.from_model(updated_category)

        except (UserIngredientCategoryNotFoundError, BuiltInIngredientCategoryError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientCategorySaveError(f"Failed to update ingredient category: {str(e)}")

    def reorder_categories(
        self, reorder_dto: UserIngredientCategoryReorderDTO
    ) -> List[UserIngredientCategoryResponseDTO]:
        """
        Reorder ingredient categories based on the provided order.

        Args:
            reorder_dto: Ordered list of ingredient category IDs

        Returns:
            List of all ingredient categories with updated positions

        Raises:
            UserIngredientCategorySaveError: If reordering fails
        """
        try:
            self._ensure_categories_exist()

            # Build position map from ordered IDs
            position_map = {
                category_id: position
                for position, category_id in enumerate(reorder_dto.ordered_ids)
            }

            # Update positions
            self.repo.bulk_update_positions(self.user_id, position_map)
            self.session.commit()

            return self.get_all_categories(include_disabled=True)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientCategorySaveError(f"Failed to reorder ingredient categories: {str(e)}")

    def bulk_update(
        self, bulk_dto: UserIngredientCategoryBulkUpdateDTO
    ) -> List[UserIngredientCategoryResponseDTO]:
        """
        Bulk update multiple ingredient categories (enabled state and position).

        Args:
            bulk_dto: List of ingredient category updates

        Returns:
            List of all ingredient categories with updated states

        Raises:
            UserIngredientCategorySaveError: If bulk update fails
        """
        try:
            self._ensure_categories_exist()

            # Convert DTOs to dicts for repository
            items = [
                {
                    "id": item.id,
                    "is_enabled": item.is_enabled,
                    "position": item.position,
                }
                for item in bulk_dto.categories
            ]

            self.repo.bulk_update(self.user_id, items)
            self.session.commit()

            return self.get_all_categories(include_disabled=True)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientCategorySaveError(f"Failed to bulk update ingredient categories: {str(e)}")

    # -- Delete Operations -----------------------------------------------------------------------
    def delete_category(self, category_id: int) -> None:
        """
        Delete a custom ingredient category.

        Args:
            category_id: ID of the ingredient category to delete

        Raises:
            UserIngredientCategoryNotFoundError: If category not found or not owned by user
            BuiltInIngredientCategoryError: If trying to delete a built-in category
            UserIngredientCategorySaveError: If deletion fails
        """
        try:
            self._ensure_categories_exist()

            # Check if category exists and is custom
            category = self.repo.get_by_id(category_id, self.user_id)
            if not category:
                raise UserIngredientCategoryNotFoundError(f"Ingredient category {category_id} not found")

            if not category.is_custom:
                raise BuiltInIngredientCategoryError(
                    "Cannot delete built-in ingredient categories. You can only disable them."
                )

            deleted = self.repo.delete(category_id, self.user_id)
            if not deleted:
                raise UserIngredientCategoryNotFoundError(f"Ingredient category {category_id} not found")

            self.session.commit()

        except (UserIngredientCategoryNotFoundError, BuiltInIngredientCategoryError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientCategorySaveError(f"Failed to delete ingredient category: {str(e)}")

    # -- Reset Operations ------------------------------------------------------------------------
    def reset_to_defaults(self) -> List[UserIngredientCategoryResponseDTO]:
        """
        Reset ingredient categories to defaults.

        - Re-enables all built-in ingredient categories
        - Disables (but keeps) all custom ingredient categories
        - Restores default ordering (built-ins first in original order, then custom)

        Returns:
            List of all ingredient categories with reset states

        Raises:
            UserIngredientCategorySaveError: If reset fails
        """
        try:
            self._ensure_categories_exist()

            # Get all categories
            all_categories = self.repo.get_all(self.user_id, include_disabled=True)

            # Separate built-in and custom
            built_in_values = [cat["value"] for cat in BUILT_IN_INGREDIENT_CATEGORIES]
            built_in_cats = []
            custom_cats = []

            for cat in all_categories:
                if cat.is_custom:
                    custom_cats.append(cat)
                else:
                    built_in_cats.append(cat)

            # Sort built-in by original order
            built_in_order = {v: i for i, v in enumerate(built_in_values)}
            built_in_cats.sort(key=lambda c: built_in_order.get(c.value, 999))

            # Update built-in: enable and set position
            for position, cat in enumerate(built_in_cats):
                cat.is_enabled = True
                cat.position = position

            # Update custom: disable and set position after built-ins
            start_position = len(built_in_cats)
            for i, cat in enumerate(custom_cats):
                cat.is_enabled = False
                cat.position = start_position + i

            self.session.flush()
            self.session.commit()

            return self.get_all_categories(include_disabled=True)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientCategorySaveError(f"Failed to reset ingredient categories: {str(e)}")
