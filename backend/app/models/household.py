"""Household sharing: one shared kitchen per member.

The household owner is the billing and data anchor. Meal plans, saved meals,
and the shopping list are stored on the owner's user id (see
``app.services.household.scope``). Recipes stay with whoever created them and
are shared explicitly through ``HouseholdRecipeShare``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base

if TYPE_CHECKING:
    from .recipe import Recipe
    from .user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Household(Base):
    """A shared kitchen. At most one membership per user."""

    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_user_id])
    members: Mapped[List["HouseholdMember"]] = relationship(
        "HouseholdMember",
        back_populates="household",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    invites: Mapped[List["HouseholdInvite"]] = relationship(
        "HouseholdInvite",
        back_populates="household",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recipe_shares: Mapped[List["HouseholdRecipeShare"]] = relationship(
        "HouseholdRecipeShare",
        back_populates="household",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class HouseholdMember(Base):
    """Membership. ``user_id`` is unique: a person belongs to one household."""

    __tablename__ = "household_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    household: Mapped["Household"] = relationship("Household", back_populates="members")
    user: Mapped["User"] = relationship("User")


class HouseholdInvite(Base):
    """A code (and optional email restriction) that adds one member.

    The app does not send email. The owner copies the link; ``email`` only
    limits which account may redeem the code.
    """

    __tablename__ = "household_invites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    household: Mapped["Household"] = relationship("Household", back_populates="invites")


class HouseholdRecipeShare(Base):
    """A recipe its owner has published into the household cookbook."""

    __tablename__ = "household_recipe_shares"
    __table_args__ = (
        UniqueConstraint("household_id", "recipe_id", name="uq_household_recipe_share"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipe.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shared_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    household: Mapped["Household"] = relationship("Household", back_populates="recipe_shares")
    recipe: Mapped["Recipe"] = relationship("Recipe")


def shared_recipe_id_select(user_id: int):
    """Recipe ids shared into the household ``user_id`` belongs to."""
    return (
        select(HouseholdRecipeShare.recipe_id)
        .join(
            HouseholdMember,
            HouseholdMember.household_id == HouseholdRecipeShare.household_id,
        )
        .where(HouseholdMember.user_id == user_id)
    )


def owner_shared_recipe_id_select(owner_user_id: int):
    """Recipe ids shared into the household owned by ``owner_user_id``."""
    return (
        select(HouseholdRecipeShare.recipe_id)
        .join(Household, Household.id == HouseholdRecipeShare.household_id)
        .where(Household.owner_user_id == owner_user_id)
    )
