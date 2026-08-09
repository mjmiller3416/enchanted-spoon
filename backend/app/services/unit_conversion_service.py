"""app/core/services/unit_conversion_service.py

Provides services for unit conversion rule management.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
import math
from typing import Dict, List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..dtos.unit_conversion_dtos import (
    UnitConversionRuleCreateDTO,
    UnitConversionRuleUpdateDTO,
)
from ..models.unit_conversion_rule import UnitConversionRule
from ..repositories.unit_conversion_repo import UnitConversionRepo


# ── Domain Exceptions ────────────────────────────────────────────────────────────────────────────────────────
class ConversionRuleNotFoundError(Exception):
    """Raised when a unit conversion rule is not found or not owned by the user."""
    pass


# ── Unit Conversion Service ────────────────────────────────────────────────────────────────────────────────
class UnitConversionService:
    """Provides unit conversion rule operations.

    All operations are scoped to a specific user for multi-tenant isolation.
    """

    def __init__(self, session: Session, user_id: int):
        """Initialize with a database session and user ID.

        Args:
            session: SQLAlchemy database session
            user_id: The ID of the current user for data isolation
        """
        self.session = session
        self.user_id = user_id
        self.repo = UnitConversionRepo(session, user_id)
        # Lazily-built lookup of the user's rules, keyed by
        # (ingredient_name, from_unit). Loaded once per service instance so
        # bulk operations (e.g. shopping sync) don't query per item.
        self._rule_map: Optional[Dict[Tuple[str, str], UnitConversionRule]] = None

    # ── CRUD Operations ─────────────────────────────────────────────────────────────────────────────────────
    def get_all(self) -> List[UnitConversionRule]:
        """Return all unit conversion rules."""
        return self.repo.get_all()

    def get_by_id(self, rule_id: int) -> Optional[UnitConversionRule]:
        """Get a single rule by ID."""
        return self.repo.get_by_id(rule_id)

    def create_rule(self, dto: UnitConversionRuleCreateDTO) -> UnitConversionRule:
        """Create a new unit conversion rule."""
        try:
            rule = UnitConversionRule(
                ingredient_name=dto.ingredient_name.lower().strip(),
                from_unit=dto.from_unit.lower().strip(),
                to_unit=dto.to_unit.lower().strip(),
                factor=dto.factor,
                round_up=dto.round_up,
                user_id=self.user_id,
            )
            self.repo.add(rule)
            self.session.commit()
            self._invalidate_rule_map()
            return rule
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def update_rule(
        self, rule_id: int, dto: UnitConversionRuleUpdateDTO
    ) -> UnitConversionRule:
        """Update an existing rule.

        Raises:
            ConversionRuleNotFoundError: If the rule doesn't exist or isn't owned by the user.
        """
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            raise ConversionRuleNotFoundError(f"Conversion rule {rule_id} not found")

        try:
            if dto.ingredient_name is not None:
                rule.ingredient_name = dto.ingredient_name.lower().strip()
            if dto.from_unit is not None:
                rule.from_unit = dto.from_unit.lower().strip()
            if dto.to_unit is not None:
                rule.to_unit = dto.to_unit.lower().strip()
            if dto.factor is not None:
                rule.factor = dto.factor
            if dto.round_up is not None:
                rule.round_up = dto.round_up

            self.session.commit()
            self._invalidate_rule_map()
            return rule
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def delete_rule(self, rule_id: int) -> None:
        """Delete a rule by ID.

        Raises:
            ConversionRuleNotFoundError: If the rule doesn't exist or isn't owned by the user.
        """
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            raise ConversionRuleNotFoundError(f"Conversion rule {rule_id} not found")

        try:
            self.repo.delete(rule)
            self.session.commit()
            self._invalidate_rule_map()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    # ── Conversion Logic ────────────────────────────────────────────────────────────────────────────────────
    def _get_rule_map(self) -> Dict[Tuple[str, str], UnitConversionRule]:
        """Load all of the user's rules once, keyed by (ingredient_name, from_unit)."""
        if self._rule_map is None:
            self._rule_map = {
                (rule.ingredient_name.lower().strip(), rule.from_unit.lower().strip()): rule
                for rule in self.repo.get_all()
            }
        return self._rule_map

    def _invalidate_rule_map(self) -> None:
        """Drop the cached rule lookup after a rule mutation."""
        self._rule_map = None

    def apply_conversion(
        self, ingredient_name: str, quantity: float, unit: str
    ) -> Tuple[float, str]:
        """
        Apply ingredient-specific conversion rule if one exists.

        Args:
            ingredient_name: Name of the ingredient (e.g., "butter")
            quantity: Quantity in the current unit
            unit: Current unit (e.g., "tbs")

        Returns:
            Tuple of (converted_quantity, converted_unit).
            Returns original values if no matching rule exists.
        """
        rule = self._get_rule_map().get(
            ((ingredient_name or "").lower().strip(), (unit or "").lower().strip())
        )
        if not rule:
            return quantity, unit

        # Convert: quantity / factor = new quantity
        # e.g., 51 tbs / 8 = 6.375 sticks
        converted = quantity / rule.factor

        # Apply rounding if specified
        if rule.round_up:
            converted = math.ceil(converted)

        return converted, rule.to_unit
