"""app/services/user_ingredient_unit_service.py

Service layer for managing user ingredient unit CRUD operations.
Orchestrates repository operations and business logic for user ingredient units.
Includes auto-seeding of built-in units on first access.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

import re
from typing import List

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session

from ..dtos.user_ingredient_unit_dtos import (
    UserIngredientUnitBulkUpdateDTO,
    UserIngredientUnitCreateDTO,
    UserIngredientUnitReorderDTO,
    UserIngredientUnitResponseDTO,
    UserIngredientUnitUpdateDTO,
)
from ..repositories.user_ingredient_unit_repo import UserIngredientUnitRepo


# -- Constants -----------------------------------------------------------------------------------
BUILT_IN_UNITS = [
    {"value": "oz", "label": "oz", "unit_type": "mass"},
    {"value": "lbs", "label": "lbs", "unit_type": "mass"},
    {"value": "tsp", "label": "tsp", "unit_type": "volume"},
    {"value": "tbs", "label": "Tbs", "unit_type": "volume"},
    {"value": "cup", "label": "cup", "unit_type": "volume"},
    {"value": "stick", "label": "stick", "unit_type": "count"},
    {"value": "bag", "label": "bag", "unit_type": "count"},
    {"value": "box", "label": "box", "unit_type": "count"},
    {"value": "can", "label": "can", "unit_type": "count"},
    {"value": "jar", "label": "jar", "unit_type": "count"},
    {"value": "package", "label": "package", "unit_type": "count"},
    {"value": "piece", "label": "piece", "unit_type": "count"},
    {"value": "slice", "label": "slice", "unit_type": "count"},
    {"value": "whole", "label": "whole", "unit_type": "count"},
    {"value": "pinch", "label": "pinch", "unit_type": "count"},
    {"value": "dash", "label": "dash", "unit_type": "count"},
    {"value": "to-taste", "label": "to taste", "unit_type": "count"},
]

MAX_CUSTOM_UNITS = 50


# -- Exceptions ----------------------------------------------------------------------------------
class UserIngredientUnitNotFoundError(Exception):
    """Raised when a user ingredient unit is not found."""

    pass


class DuplicateUserIngredientUnitError(Exception):
    """Raised when attempting to create a unit with a duplicate slug."""

    pass


class UserIngredientUnitSaveError(Exception):
    """Raised when a user ingredient unit cannot be saved."""

    pass


class BuiltInIngredientUnitError(Exception):
    """Raised when attempting to delete or rename a built-in unit."""

    pass


class IngredientUnitLimitExceededError(Exception):
    """Raised when user has reached the maximum number of custom units."""

    pass


# -- UserIngredientUnit Service ------------------------------------------------------------------
class UserIngredientUnitService:
    """Service for user ingredient unit operations with business logic."""

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the UserIngredientUnitService with a database session and user ID.

        Args:
            session: SQLAlchemy database session (required).
            user_id: ID of the authenticated user (required for multi-tenant isolation).
        """
        self.session = session
        self.user_id = user_id
        self.repo = UserIngredientUnitRepo(self.session)

    # -- Private Helpers -------------------------------------------------------------------------
    def _ensure_units_exist(self) -> None:
        """
        Ensure the user has ingredient units seeded.

        If the user has no units, seed the built-in defaults.
        This is called at the start of operations to ensure auto-seeding.
        """
        count = self.repo.count(self.user_id)
        if count == 0:
            self.repo.seed_defaults(self.user_id, BUILT_IN_UNITS)
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
    def create_unit(self, create_dto: UserIngredientUnitCreateDTO) -> UserIngredientUnitResponseDTO:
        """
        Create a new custom ingredient unit for the current user.

        Custom units are always of type "count".

        Args:
            create_dto: Data for creating the unit

        Returns:
            Created unit as DTO

        Raises:
            IngredientUnitLimitExceededError: If user has reached max custom units
            DuplicateUserIngredientUnitError: If a unit with this slug already exists
            UserIngredientUnitSaveError: If the unit cannot be saved
        """
        try:
            self._ensure_units_exist()

            # Check custom unit limit
            custom_count = self.repo.count_custom(self.user_id)
            if custom_count >= MAX_CUSTOM_UNITS:
                raise IngredientUnitLimitExceededError(
                    f"Maximum {MAX_CUSTOM_UNITS} custom ingredient units allowed"
                )

            # Generate slug from label
            base_slug = self._generate_slug(create_dto.label)
            if not base_slug:
                raise UserIngredientUnitSaveError("Could not generate a valid slug from the label")

            slug = self._ensure_unique_slug(base_slug)

            # Get next position
            max_position = self.repo.get_max_position(self.user_id)
            new_position = max_position + 1

            # Create the unit (custom units are always "count" type)
            unit = self.repo.create(
                user_id=self.user_id,
                value=slug,
                label=create_dto.label,
                is_custom=True,
                position=new_position,
                unit_type="count",
            )
            self.session.commit()

            return UserIngredientUnitResponseDTO.from_model(unit)

        except (IngredientUnitLimitExceededError, DuplicateUserIngredientUnitError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientUnitSaveError(f"Failed to create ingredient unit: {str(e)}")

    # -- Read Operations -------------------------------------------------------------------------
    def get_all_units(
        self, include_disabled: bool = False
    ) -> List[UserIngredientUnitResponseDTO]:
        """
        Get all ingredient units for the current user.

        Args:
            include_disabled: If True, include disabled units

        Returns:
            List of all units belonging to the user
        """
        self._ensure_units_exist()

        units = self.repo.get_all(self.user_id, include_disabled=include_disabled)
        return [UserIngredientUnitResponseDTO.from_model(u) for u in units]

    def get_unit_by_id(self, unit_id: int) -> UserIngredientUnitResponseDTO:
        """
        Get an ingredient unit by ID.

        Args:
            unit_id: ID of the unit to retrieve

        Returns:
            Unit as DTO

        Raises:
            UserIngredientUnitNotFoundError: If unit not found or not owned by user
        """
        self._ensure_units_exist()

        unit = self.repo.get_by_id(unit_id, self.user_id)
        if not unit:
            raise UserIngredientUnitNotFoundError(f"Ingredient unit {unit_id} not found")

        return UserIngredientUnitResponseDTO.from_model(unit)

    # -- Update Operations -----------------------------------------------------------------------
    def update_unit(
        self, unit_id: int, update_dto: UserIngredientUnitUpdateDTO
    ) -> UserIngredientUnitResponseDTO:
        """
        Update an ingredient unit.

        Args:
            unit_id: ID of the unit to update
            update_dto: Data for updating the unit

        Returns:
            Updated unit as DTO

        Raises:
            UserIngredientUnitNotFoundError: If unit not found or not owned by user
            BuiltInIngredientUnitError: If trying to rename a built-in unit
            UserIngredientUnitSaveError: If the unit cannot be updated
        """
        try:
            self._ensure_units_exist()

            # Check if unit exists
            unit = self.repo.get_by_id(unit_id, self.user_id)
            if not unit:
                raise UserIngredientUnitNotFoundError(f"Ingredient unit {unit_id} not found")

            # Cannot rename built-in units
            if update_dto.label is not None and not unit.is_custom:
                raise BuiltInIngredientUnitError(
                    "Cannot rename built-in ingredient units. You can only enable/disable them."
                )

            # Update the unit
            updated_unit = self.repo.update(
                unit_id=unit_id,
                user_id=self.user_id,
                label=update_dto.label,
                is_enabled=update_dto.is_enabled,
            )
            self.session.commit()

            if not updated_unit:
                raise UserIngredientUnitNotFoundError(f"Ingredient unit {unit_id} not found")

            return UserIngredientUnitResponseDTO.from_model(updated_unit)

        except (UserIngredientUnitNotFoundError, BuiltInIngredientUnitError, ValueError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientUnitSaveError(f"Failed to update ingredient unit: {str(e)}")

    def reorder_units(
        self, reorder_dto: UserIngredientUnitReorderDTO
    ) -> List[UserIngredientUnitResponseDTO]:
        """
        Reorder ingredient units based on the provided order.

        Args:
            reorder_dto: Ordered list of unit IDs

        Returns:
            List of all units with updated positions

        Raises:
            UserIngredientUnitSaveError: If reordering fails
        """
        try:
            self._ensure_units_exist()

            # Build position map from ordered IDs
            position_map = {
                unit_id: position
                for position, unit_id in enumerate(reorder_dto.ordered_ids)
            }

            # Update positions
            self.repo.bulk_update_positions(self.user_id, position_map)
            self.session.commit()

            return self.get_all_units(include_disabled=True)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientUnitSaveError(f"Failed to reorder ingredient units: {str(e)}")

    def bulk_update(
        self, bulk_dto: UserIngredientUnitBulkUpdateDTO
    ) -> List[UserIngredientUnitResponseDTO]:
        """
        Bulk update multiple ingredient units (enabled state and position).

        Args:
            bulk_dto: List of unit updates

        Returns:
            List of all units with updated states

        Raises:
            UserIngredientUnitSaveError: If bulk update fails
        """
        try:
            self._ensure_units_exist()

            # Convert DTOs to dicts for repository
            items = [
                {
                    "id": item.id,
                    "is_enabled": item.is_enabled,
                    "position": item.position,
                }
                for item in bulk_dto.units
            ]

            self.repo.bulk_update(self.user_id, items)
            self.session.commit()

            return self.get_all_units(include_disabled=True)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientUnitSaveError(f"Failed to bulk update ingredient units: {str(e)}")

    # -- Delete Operations -----------------------------------------------------------------------
    def delete_unit(self, unit_id: int) -> None:
        """
        Delete a custom ingredient unit.

        Args:
            unit_id: ID of the unit to delete

        Raises:
            UserIngredientUnitNotFoundError: If unit not found or not owned by user
            BuiltInIngredientUnitError: If trying to delete a built-in unit
            UserIngredientUnitSaveError: If deletion fails
        """
        try:
            self._ensure_units_exist()

            # Check if unit exists and is custom
            unit = self.repo.get_by_id(unit_id, self.user_id)
            if not unit:
                raise UserIngredientUnitNotFoundError(f"Ingredient unit {unit_id} not found")

            if not unit.is_custom:
                raise BuiltInIngredientUnitError(
                    "Cannot delete built-in ingredient units. You can only disable them."
                )

            deleted = self.repo.delete(unit_id, self.user_id)
            if not deleted:
                raise UserIngredientUnitNotFoundError(f"Ingredient unit {unit_id} not found")

            self.session.commit()

        except (UserIngredientUnitNotFoundError, BuiltInIngredientUnitError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientUnitSaveError(f"Failed to delete ingredient unit: {str(e)}")

    # -- Reset Operations ------------------------------------------------------------------------
    def reset_to_defaults(self) -> List[UserIngredientUnitResponseDTO]:
        """
        Reset ingredient units to defaults.

        - Re-enables all built-in units
        - Disables (but keeps) all custom units
        - Restores default ordering (built-ins first in original order, then custom)

        Returns:
            List of all units with reset states

        Raises:
            UserIngredientUnitSaveError: If reset fails
        """
        try:
            self._ensure_units_exist()

            # Get all units
            all_units = self.repo.get_all(self.user_id, include_disabled=True)

            # Separate built-in and custom
            built_in_values = [u["value"] for u in BUILT_IN_UNITS]
            built_in_units = []
            custom_units = []

            for unit in all_units:
                if unit.is_custom:
                    custom_units.append(unit)
                else:
                    built_in_units.append(unit)

            # Sort built-in by original order
            built_in_order = {v: i for i, v in enumerate(built_in_values)}
            built_in_units.sort(key=lambda u: built_in_order.get(u.value, 999))

            # Update built-in: enable and set position
            for position, unit in enumerate(built_in_units):
                unit.is_enabled = True
                unit.position = position

            # Update custom: disable and set position after built-ins
            start_position = len(built_in_units)
            for i, unit in enumerate(custom_units):
                unit.is_enabled = False
                unit.position = start_position + i

            self.session.flush()
            self.session.commit()

            return self.get_all_units(include_disabled=True)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserIngredientUnitSaveError(f"Failed to reset ingredient units: {str(e)}")
