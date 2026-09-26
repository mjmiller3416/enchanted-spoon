"""app/services/user_category_service.py

Service layer for managing user category CRUD operations.
Orchestrates repository operations and business logic for user categories.
Includes auto-seeding of built-in categories on first access.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

import re
from typing import List

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session

from ..dtos.user_category_dtos import (
    UserCategoryBulkUpdateDTO,
    UserCategoryCreateDTO,
    UserCategoryReorderDTO,
    UserCategoryResponseDTO,
    UserCategoryUpdateDTO,
)
from ..repositories.user_category_repo import UserCategoryRepo


# -- Constants -----------------------------------------------------------------------------------
BUILT_IN_CATEGORIES = [
    {"value": "american", "label": "American"},
    {"value": "chinese", "label": "Chinese"},
    {"value": "french", "label": "French"},
    {"value": "indian", "label": "Indian"},
    {"value": "italian", "label": "Italian"},
    {"value": "japanese", "label": "Japanese"},
    {"value": "mediterranean", "label": "Mediterranean"},
    {"value": "mexican", "label": "Mexican"},
    {"value": "thai", "label": "Thai"},
]

MAX_CUSTOM_CATEGORIES = 50


# -- Exceptions ----------------------------------------------------------------------------------
class UserCategoryNotFoundError(Exception):
    """Raised when a user category is not found."""

    pass


class DuplicateUserCategoryError(Exception):
    """Raised when attempting to create a category with a duplicate slug."""

    pass


class UserCategorySaveError(Exception):
    """Raised when a user category cannot be saved."""

    pass


class BuiltInCategoryError(Exception):
    """Raised when attempting to delete or rename a built-in category."""

    pass


class CategoryLimitExceededError(Exception):
    """Raised when user has reached the maximum number of custom categories."""

    pass


# -- UserCategory Service ------------------------------------------------------------------------
class UserCategoryService:
    """Service for user category operations with business logic."""

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the UserCategoryService with a database session and user ID.

        Args:
            session: SQLAlchemy database session (required).
            user_id: ID of the authenticated user (required for multi-tenant isolation).
        """
        self.session = session
        self.user_id = user_id
        self.repo = UserCategoryRepo(self.session)

    # -- Private Helpers -------------------------------------------------------------------------
    def _ensure_categories_exist(self) -> None:
        """
        Ensure the user has categories seeded.

        If the user has no categories, seed the built-in defaults.
        This is called at the start of operations to ensure auto-seeding.
        """
        count = self.repo.count(self.user_id)
        if count == 0:
            self.repo.seed_defaults(self.user_id, BUILT_IN_CATEGORIES)
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
    def create_category(self, create_dto: UserCategoryCreateDTO) -> UserCategoryResponseDTO:
        """
        Create a new custom category for the current user.

        Args:
            create_dto: Data for creating the category

        Returns:
            Created category as DTO

        Raises:
            CategoryLimitExceededError: If user has reached max custom categories
            DuplicateUserCategoryError: If a category with this slug already exists
            UserCategorySaveError: If the category cannot be saved
        """
        try:
            self._ensure_categories_exist()

            # Check custom category limit
            custom_count = self.repo.count_custom(self.user_id)
            if custom_count >= MAX_CUSTOM_CATEGORIES:
                raise CategoryLimitExceededError(
                    f"Maximum {MAX_CUSTOM_CATEGORIES} custom categories allowed"
                )

            # Generate slug from label
            base_slug = self._generate_slug(create_dto.label)
            if not base_slug:
                raise UserCategorySaveError("Could not generate a valid slug from the label")

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

            return UserCategoryResponseDTO.from_model(category)

        except (CategoryLimitExceededError, DuplicateUserCategoryError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserCategorySaveError(f"Failed to create category: {str(e)}")

    # -- Read Operations -------------------------------------------------------------------------
    def get_all_categories(
        self, include_disabled: bool = False
    ) -> List[UserCategoryResponseDTO]:
        """
        Get all categories for the current user.

        Args:
            include_disabled: If True, include disabled categories

        Returns:
            List of all categories belonging to the user
        """
        self._ensure_categories_exist()

        categories = self.repo.get_all(self.user_id, include_disabled=include_disabled)
        return [UserCategoryResponseDTO.from_model(cat) for cat in categories]

    def get_category_by_id(self, category_id: int) -> UserCategoryResponseDTO:
        """
        Get a category by ID.

        Args:
            category_id: ID of the category to retrieve

        Returns:
            Category as DTO

        Raises:
            UserCategoryNotFoundError: If category not found or not owned by user
        """
        self._ensure_categories_exist()

        category = self.repo.get_by_id(category_id, self.user_id)
        if not category:
            raise UserCategoryNotFoundError(f"Category {category_id} not found")

        return UserCategoryResponseDTO.from_model(category)

    # -- Update Operations -----------------------------------------------------------------------
    def update_category(
        self, category_id: int, update_dto: UserCategoryUpdateDTO
    ) -> UserCategoryResponseDTO:
        """
        Update a category.

        Args:
            category_id: ID of the category to update
            update_dto: Data for updating the category

        Returns:
            Updated category as DTO

        Raises:
            UserCategoryNotFoundError: If category not found or not owned by user
            BuiltInCategoryError: If trying to rename a built-in category
            UserCategorySaveError: If the category cannot be updated
        """
        try:
            self._ensure_categories_exist()

            # Check if category exists
            category = self.repo.get_by_id(category_id, self.user_id)
            if not category:
                raise UserCategoryNotFoundError(f"Category {category_id} not found")

            # Cannot rename built-in categories
            if update_dto.label is not None and not category.is_custom:
                raise BuiltInCategoryError(
                    "Cannot rename built-in categories. You can only enable/disable them."
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
                raise UserCategoryNotFoundError(f"Category {category_id} not found")

            return UserCategoryResponseDTO.from_model(updated_category)

        except (UserCategoryNotFoundError, BuiltInCategoryError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserCategorySaveError(f"Failed to update category: {str(e)}")

    def reorder_categories(
        self, reorder_dto: UserCategoryReorderDTO
    ) -> List[UserCategoryResponseDTO]:
        """
        Reorder categories based on the provided order.

        Args:
            reorder_dto: Ordered list of category IDs

        Returns:
            List of all categories with updated positions

        Raises:
            UserCategorySaveError: If reordering fails
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
            raise UserCategorySaveError(f"Failed to reorder categories: {str(e)}")

    def bulk_update(
        self, bulk_dto: UserCategoryBulkUpdateDTO
    ) -> List[UserCategoryResponseDTO]:
        """
        Bulk update multiple categories (enabled state and position).

        Args:
            bulk_dto: List of category updates

        Returns:
            List of all categories with updated states

        Raises:
            UserCategorySaveError: If bulk update fails
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
            raise UserCategorySaveError(f"Failed to bulk update categories: {str(e)}")

    # -- Delete Operations -----------------------------------------------------------------------
    def delete_category(self, category_id: int) -> None:
        """
        Delete a custom category.

        Args:
            category_id: ID of the category to delete

        Raises:
            UserCategoryNotFoundError: If category not found or not owned by user
            BuiltInCategoryError: If trying to delete a built-in category
            UserCategorySaveError: If deletion fails
        """
        try:
            self._ensure_categories_exist()

            # Check if category exists and is custom
            category = self.repo.get_by_id(category_id, self.user_id)
            if not category:
                raise UserCategoryNotFoundError(f"Category {category_id} not found")

            if not category.is_custom:
                raise BuiltInCategoryError(
                    "Cannot delete built-in categories. You can only disable them."
                )

            deleted = self.repo.delete(category_id, self.user_id)
            if not deleted:
                raise UserCategoryNotFoundError(f"Category {category_id} not found")

            self.session.commit()

        except (UserCategoryNotFoundError, BuiltInCategoryError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserCategorySaveError(f"Failed to delete category: {str(e)}")

    # -- Reset Operations ------------------------------------------------------------------------
    def reset_to_defaults(self) -> List[UserCategoryResponseDTO]:
        """
        Reset categories to defaults.

        - Re-enables all built-in categories
        - Disables (but keeps) all custom categories
        - Restores default ordering (built-ins first in original order, then custom)

        Returns:
            List of all categories with reset states

        Raises:
            UserCategorySaveError: If reset fails
        """
        try:
            self._ensure_categories_exist()

            # Get all categories
            all_categories = self.repo.get_all(self.user_id, include_disabled=True)

            # Separate built-in and custom
            built_in_values = [cat["value"] for cat in BUILT_IN_CATEGORIES]
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
            raise UserCategorySaveError(f"Failed to reset categories: {str(e)}")
