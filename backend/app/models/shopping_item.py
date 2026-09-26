"""app/core/models/shopping_item.py

SQLAlchemy ORM model for shopping list items.
Handles both recipe-generated and manually added shopping items.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base
from ..utils.unit_conversion import get_dimension

if TYPE_CHECKING:
    from .shopping_item_contribution import ShoppingItemContribution
    from .user import User


# ── Shopping Item Model ─────────────────────────────────────────────────────────────────────────────────────
class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    __table_args__ = (
        UniqueConstraint("aggregation_key", "user_id", name="uq_shopping_item_aggregation_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # source and status
    # "recipe" = planner sync, "manual" = in-app quick add, anything else = the slug of a
    # trusted external app pushing via the API-key ingest endpoint (e.g. "tada")
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
        index=True
    )
    have: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Unique key for aggregation: "ingredient_name::dimension"
    # Used to identify items for diff-based sync (recipe items only)
    aggregation_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # User ownership
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Relationships ──────────────────────────────────────────────────────────────────────────────────────
    # Contributions from planner entries (cascade delete when item is deleted)
    contributions: Mapped[List["ShoppingItemContribution"]] = relationship(
        "ShoppingItemContribution",
        back_populates="shopping_item",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # User ownership
    user: Mapped["User"] = relationship("User", back_populates="shopping_items")

    # ── String Representation ───────────────────────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<ShoppingItem(id={self.id}, name='{self.ingredient_name}', qty={self.quantity}, have={self.have})>"

    # ── Helper Methods ──────────────────────────────────────────────────────────────────────────────────────
    def get_aggregation_key(self) -> str:
        """Generate the aggregation key for this shopping item using dimension."""
        if self.aggregation_key:
            return self.aggregation_key
        dimension = get_dimension(self.unit)
        return f"{self.ingredient_name.lower().strip()}::{dimension}"

    @staticmethod
    def make_aggregation_key(ingredient_name: str, dimension: str) -> str:
        """Create an aggregation key from ingredient name and dimension.

        The name part is capped so the key always fits the String(255) column.
        """
        return f"{ingredient_name.lower().strip()[:200]}::{dimension}"

    def get_recipe_sources(self) -> List[str]:
        """Get list of recipe names that contribute to this item from contributions."""
        if not self.contributions:
            return []
        # We need to load recipe names from contributions
        # This requires the relationship to be loaded
        recipe_names: set[str] = set()
        for contrib in self.contributions:
            # Access recipe through lazy load if needed
            if hasattr(contrib, 'recipe') and contrib.recipe:
                recipe_names.add(contrib.recipe.recipe_name)
        return sorted(list(recipe_names))

    def display_label(self) -> str:
        """Return a human-friendly label for UI display."""
        icon = "✓" if self.have else "○"
        unit_display = f" {self.unit}" if self.unit else ""
        return f"{icon} {self.ingredient_name}: {self.quantity}{unit_display}"

    def formatted_quantity(self) -> str:
        """Return formatted quantity string."""
        if self.quantity == int(self.quantity):
            return str(int(self.quantity))
        return f"{self.quantity:.2f}".rstrip('0').rstrip('.')

    @classmethod
    def create_from_recipe(
        cls,
        ingredient_name: str,
        quantity: float,
        unit: Optional[str] = None,
        category: Optional[str] = None,
        aggregation_key: Optional[str] = None
        ) -> "ShoppingItem":
        """
        Create a shopping item from recipe data.

        Args:
            ingredient_name (str): The name of the ingredient.
            quantity (float): The quantity of the ingredient.
            unit (Optional[str]): The unit of measurement, if any.
            category (Optional[str]): The category of the ingredient.
            aggregation_key (Optional[str]): The aggregation key for this item.

        Returns:
            ShoppingItem: A new shopping item instance.
        """
        # Generate aggregation key if not provided
        if not aggregation_key:
            dimension = get_dimension(unit)
            aggregation_key = cls.make_aggregation_key(ingredient_name, dimension)

        return cls(
            ingredient_name=ingredient_name,
            quantity=quantity,
            unit=unit,
            category=category,
            source="recipe",
            have=False,
            aggregation_key=aggregation_key
        )

    @staticmethod
    def make_external_aggregation_key(source: str, ingredient_name: str) -> str:
        """Create the dedupe key for an externally pushed item.

        The "external::" prefix keeps these keys out of the recipe sync namespace
        ("name::dimension"); the (aggregation_key, user_id) unique constraint then
        enforces one row per (source, name) per user at the DB level.
        """
        # Truncate the name portion so the key always fits the 255-char column
        name = ingredient_name.lower().strip()[:200]
        return f"external::{source.lower().strip()}::{name}"

    @classmethod
    def create_external(
        cls,
        ingredient_name: str,
        source: str,
        quantity: float = 1.0,
        unit: Optional[str] = None,
        category: Optional[str] = None
        ) -> "ShoppingItem":
        """
        Create a shopping item pushed by a trusted external app.

        Args:
            ingredient_name (str): The name of the item.
            source (str): Slug of the pushing app (e.g. "tada").
            quantity (float): The quantity of the item.
            unit (Optional[str]): The unit of measurement, if any.
            category (Optional[str]): The category for the item (e.g. "household").

        Returns:
            ShoppingItem: A new external shopping item instance.
        """
        return cls(
            ingredient_name=ingredient_name,
            quantity=quantity,
            unit=unit,
            category=category,
            source=source,
            have=False,
            aggregation_key=cls.make_external_aggregation_key(source, ingredient_name)
        )

    @classmethod
    def create_manual(
        cls,
        ingredient_name: str,
        quantity: float,
        unit: Optional[str] = None,
        category: Optional[str] = None
        ) -> "ShoppingItem":
        """
        Create a manual shopping item.

        Args:
            ingredient_name (str): The name of the ingredient.
            quantity (float): The quantity of the ingredient.
            unit (Optional[str]): The unit of measurement, if any.
            category (Optional[str]): The category for the ingredient.

        Returns:
            ShoppingItem: A new manual shopping item instance.
        """
        return cls(
            ingredient_name=ingredient_name,
            quantity=quantity,
            unit=unit,
            category=category or "other",
            source="manual",
            have=False
        )
