"""app/models/user.py

SQLAlchemy ORM model for application users.
Integrates with Clerk for authentication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.access_policy import (
    ACCESS_READ_ONLY,
    as_utc,
    free_plan_sunset,
    is_existing_free_cohort,
    resolve_access_mode,
)
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

    # First free trial this account has used, on any billing provider.
    # A later trial from Stripe or a store does not grant Pro.
    trial_consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    trial_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # App Store / Play Billing entitlement (RevenueCat). Kept off the Stripe
    # columns so a store receipt and a Stripe subscription cannot clobber
    # each other.
    store_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    store_product_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    store_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    store_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    store_will_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    store_original_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    store_environment: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    store_event_timestamp_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Granted access fields (for testers, promos)
    granted_pro_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    # Last authenticated request, stamped at most every few minutes (see UserService.touch_last_active)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    def _store_is_current(self, now: Optional[datetime] = None) -> bool:
        """True when the store entitlement itself grants Pro right now."""
        if self.store_status not in ACTIVE_SUBSCRIPTION_STATUSES:
            return False
        if self.store_expires_at is None:
            return True
        now = now or datetime.now(timezone.utc)
        return as_utc(self.store_expires_at) > as_utc(now)

    @property
    def has_pro_access(self) -> bool:
        """Check if user has pro-level access through any path."""
        # Admins always have full access
        if self.is_admin:
            return True

        # Active paid Stripe subscription
        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return True

        # Active App Store or Play Billing entitlement
        if self._store_is_current():
            return True

        # Granted temporary access (testers, promos)
        if self.granted_pro_until:
            if as_utc(self.granted_pro_until) > datetime.now(timezone.utc):
                return True

        return False

    @property
    def billing_channel(self) -> Optional[str]:
        """Where the current paid plan is billed: store provider or ``stripe``."""
        if self._store_is_current():
            return self.store_provider
        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return "stripe"
        return None

    @property
    def access_mode(self) -> str:
        """``full`` or ``read_only``. Read-only accounts can view and export."""
        return resolve_access_mode(
            is_admin=self.is_admin,
            has_pro_access=self.has_pro_access,
            created_at=self.created_at,
            now=datetime.now(timezone.utc),
        )

    @property
    def grandfathered_free_until(self) -> Optional[datetime]:
        """When an existing free account stops being a full free plan, if ever."""
        if self.is_admin or self.has_pro_access:
            return None
        if not is_existing_free_cohort(self.created_at):
            return None
        return free_plan_sunset()

    @property
    def access_reason(self) -> str:
        """Why does this user have their current access level? (for debugging/support)"""
        if self.is_admin:
            return "admin"
        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return "subscription"
        if self._store_is_current():
            return "store_subscription"
        if self.granted_pro_until and as_utc(self.granted_pro_until) > datetime.now(timezone.utc):
            return f"granted ({self.granted_by or 'manual'})"
        if self.access_mode == ACCESS_READ_ONLY:
            return "read_only"
        if self.grandfathered_free_until is not None:
            return "grandfathered_free"
        return "free"

    # ── Helper Methods ──────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', access='{self.access_reason}')>"
