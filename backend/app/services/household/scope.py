"""Resolve whose meal plan and shopping list a request should use.

Joining a household points planner, meals, and shopping at the household
owner's rows. Recipes are not moved; callers that should see the shared
cookbook use ``shared_recipe_id_select``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.household import Household, HouseholdMember
from ...models.user import User


@dataclass(frozen=True)
class KitchenScope:
    """Actor plus the user id that owns the shared kitchen data."""

    actor_id: int
    kitchen_user_id: int
    household_id: Optional[int]
    role: Optional[str]


def membership_for(session: Session, user_id: int) -> Optional[HouseholdMember]:
    """The user's membership, or None when they are not in a household."""
    stmt = select(HouseholdMember).where(HouseholdMember.user_id == user_id)
    return session.scalars(stmt).first()


def resolve_kitchen(session: Session, user: User) -> KitchenScope:
    """Meal plan and shopping list live on the household owner."""
    member = membership_for(session, user.id)
    if member is None:
        return KitchenScope(
            actor_id=user.id,
            kitchen_user_id=user.id,
            household_id=None,
            role=None,
        )
    household = session.get(Household, member.household_id)
    if household is None:
        return KitchenScope(
            actor_id=user.id,
            kitchen_user_id=user.id,
            household_id=None,
            role=None,
        )
    return KitchenScope(
        actor_id=user.id,
        kitchen_user_id=household.owner_user_id,
        household_id=household.id,
        role=member.role,
    )


def kitchen_user_id(session: Session, user: User) -> int:
    """User id whose planner, meals, and shopping list this person edits."""
    return resolve_kitchen(session, user).kitchen_user_id


def effective_access(session: Session, user: User) -> tuple[bool, str]:
    """Pro access for feature gates.

    A member without their own Pro subscription is covered while the household
    owner has Pro (paid, granted, or admin). Usage counters stay on the member.
    The owner's own access is unchanged. Coverage never downgrades someone who
    already has Pro.
    """
    if user.has_pro_access:
        return True, user.access_reason

    scope = resolve_kitchen(session, user)
    if scope.household_id is None or scope.kitchen_user_id == user.id:
        return False, user.access_reason

    owner = session.get(User, scope.kitchen_user_id)
    if owner is not None and owner.has_pro_access:
        return True, "household"
    return False, user.access_reason
