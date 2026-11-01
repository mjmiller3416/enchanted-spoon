"""app/models/user.py

SQLAlchemy ORM model for application users.
Integrates with Clerk for authentication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, false as sql_false
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

    # Existing rows retain legacy allowances; only newly created ORM accounts
    # receive the launch plan. Never accept this field from a client payload.
    usage_plan: Mapped[str] = mapped_column(String(20), default="launch", server_default="legacy", nullable=False)
    # Admin override. Pro-tier accounts with this flag keep the pre-release
    # allowances instead of the launch caps. Does not grant Pro or admin.
    usage_exempt: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sql_false(), nullable=False)

    # Trial window. Null until Stripe reports a trialing subscription.
    trial_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    has_used_trial: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sql_false(), nullable=False)
    # Checkout session that claimed the trial. Cleared when the session expires unused.
    pending_trial_checkout_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Set by the free-tier sunset job. Null means the account is not read-only
    # unless the sunset date has already passed for a legacy free account.
    read_only_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sunset_notice_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sunset_reminder_30_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sunset_reminder_7_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sunset_reminder_1_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @property
    def has_pro_access(self) -> bool:
        """Check if user has pro-level access through any path.

        Trialing stays inside this gate so Pro features stay visible during
        the 7-day trial. Usage caps use ``usage_tier``, which is stricter.
        """
        if self.keeps_admin_access():
            return True

        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return True

        if self.granted_pro_until and self._aware(self.granted_pro_until) > datetime.now(timezone.utc):
            return True

        return False

    def is_legacy_free_account(self) -> bool:
        """Free account created before ``LEGACY_FREE_CUTOFF``.

        Those accounts keep the free plan until the sunset date. The cutoff
        is the coordinated release deploy time. ``usage_plan`` is a separate
        allowance cohort and does not decide this.
        """
        from ..core.offer_windows import created_before_legacy_free_cutoff

        return (
            not self.keeps_admin_access()
            and created_before_legacy_free_cutoff(self.created_at)
            and self.subscription_tier == "free"
            and self.subscription_status == "active"
            and not self.has_used_trial
            and not (
                self.granted_pro_until
                and self._aware(self.granted_pro_until) > datetime.now(timezone.utc)
            )
        )

    @property
    def is_read_only(self) -> bool:
        """View and export only. Create, plan, and AI are locked."""
        if self.keeps_admin_access() or self.has_pro_access:
            return False
        if self.read_only_at is not None:
            return True
        from ..core.offer_windows import sunset_is_due

        return self.is_legacy_free_account() and sunset_is_due()

    @property
    def usage_tier(self) -> str:
        """Cap tier: pro, trial, free, or expired.

        Admins and active grants use pro (admins are then uncapped by the
        caller). A trialing subscription past ``trial_ends_at`` is expired.
        Only accounts created before ``LEGACY_FREE_CUTOFF`` stay on the
        metered free plan until the sunset date. Accounts created on or
        after that cutoff have no recurring free AI allowance (``none``).
        After the sunset date, legacy free accounts are read-only and
        resolve to expired (zero AI).
        """
        now = datetime.now(timezone.utc)
        if self.keeps_admin_access():
            return "pro"
        if self.granted_pro_until and self._aware(self.granted_pro_until) > now:
            return "pro"
        if self.subscription_tier == "pro" and self.subscription_status == "trialing":
            if self.trial_ends_at is not None and self._aware(self.trial_ends_at) <= now:
                return "expired"
            return "trial"
        if self.subscription_tier == "pro" and self.subscription_status in {"active", "past_due"}:
            return "pro"
        if self.is_read_only:
            return "expired"
        if self.is_legacy_free_account():
            return "free"
        if (
            self.subscription_tier == "free"
            and self.subscription_status == "active"
            and not self.has_used_trial
        ):
            return "none"
        return "expired"

    @property
    def access_reason(self) -> str:
        """Why does this user have their current access level? (for debugging/support)"""
        if self.keeps_admin_access():
            return "admin"
        if self.usage_tier == "trial":
            return "trial"
        if self.subscription_tier == "pro" and self.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
            return "subscription"
        if self.granted_pro_until and self._aware(self.granted_pro_until) > datetime.now(timezone.utc):
            return f"granted ({self.granted_by or 'manual'})"
        if self.is_read_only:
            return "read_only"
        if self.usage_tier == "none":
            return "trial_required"
        if self.usage_tier == "expired":
            return "expired"
        return "free"

    def keeps_admin_access(self) -> bool:
        """Database admin flag only.

        ``ADMIN_EXEMPT_EMAILS`` does not grant this. Those accounts get
        uncapped AI only, after Clerk confirms the verified primary email.
        """
        return bool(self.is_admin)

    # ── Helper Methods ──────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', access='{self.access_reason}')>"
