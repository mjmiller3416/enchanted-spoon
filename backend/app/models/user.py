"""app/models/user.py

SQLAlchemy ORM model for application users.
Integrates with Clerk for authentication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base

if TYPE_CHECKING:
    from .meal import Meal
    from .planner_entry import PlannerEntry
    from .recipe import Recipe
    from .recipe_group import RecipeGroup
    from .recipe_history import RecipeHistory
    from .shopping_item import ShoppingItem
    from .user_category import UserCategory
    from .user_ingredient_category import UserIngredientCategory
    from .user_ingredient_unit import UserIngredientUnit
    from .user_usage import UserUsage


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


# Stripe subscription statuses that keep pro access. Anything else (canceled,
# unpaid, incomplete_expired, ...) is treated as no longer paying. Shared with
# the Stripe webhook handler so access checks and webhook writes agree.
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due"}


class User(Base):
    """
    Application user linked to Clerk authentication.

    Users own recipes, meals, planner entries, and shopping items.
    The clerk_id links to the external Clerk user for JWT validation.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Clerk integration
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # User info (synced from Clerk)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Admin flag - permanent full access bypass
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Subscription fields (Stripe-managed)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    subscription_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # True when Stripe will stop the subscription at the current period end
    # (portal cancel) — subscription_ends_at is then an end date, not a renewal.
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Granted access fields (for testers, promos)
    granted_pro_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # ── Relationships ───────────────────────────────────────────────────────
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    meals: Mapped[List["Meal"]] = relationship(
        "Meal",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    planner_entries: Mapped[List["PlannerEntry"]] = relationship(
        "PlannerEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    shopping_items: Mapped[List["ShoppingItem"]] = relationship(
        "ShoppingItem",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    recipe_history: Mapped[List["RecipeHistory"]] = relationship(
        "RecipeHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    usage_records: Mapped[List["UserUsage"]] = relationship(
        "UserUsage",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    recipe_groups: Mapped[List["RecipeGroup"]] = relationship(
        "RecipeGroup",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    categories: Mapped[List["UserCategory"]] = relationship(
        "UserCategory",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    ingredient_categories: Mapped[List["UserIngredientCategory"]] = relationship(
        "UserIngredientCategory",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    ingredient_units: Mapped[List["UserIngredientUnit"]] = relationship(
        "UserIngredientUnit",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # ── Properties ──────────────────────────────────────────────────────────
    @property
    def has_pro_access(self) -> bool:
        """Check if user has pro-level access through any path."""
        # Admins always have full access
        if self.is_admin:
            return True

        # Active paid subscription
        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return True

        # Granted temporary access (testers, promos)
        if self.granted_pro_until:
            if self.granted_pro_until > datetime.now(timezone.utc):
                return True

        return False

    @property
    def access_reason(self) -> str:
        """Why does this user have their current access level? (for debugging/support)"""
        if self.is_admin:
            return "admin"
        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return "subscription"
        if self.granted_pro_until and self.granted_pro_until > datetime.now(timezone.utc):
            return f"granted ({self.granted_by or 'manual'})"
        return "free"

    # ── Helper Methods ──────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', access='{self.access_reason}')>"
