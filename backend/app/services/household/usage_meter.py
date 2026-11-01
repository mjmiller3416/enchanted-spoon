"""Shared usage meter for a household of two or more people.

The multiplier and the choice of whose row to charge live here, not in
``app.core.usage_limits``. That module only supplies the Pro base caps, so a
change to the tier table does not have to know about households.

A household with one person (the owner alone) keeps that person's own meter
and tier cap. Once a second member joins, every capped AI call — the owner's
and every member's — reserves against the owner's monthly row. The cap is the
Pro cap times ``HOUSEHOLD_CAP_MULTIPLIER``. The owner's admin flag still
means uncapped; a member's admin flag does not open a private meter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.usage_limits import get_monthly_limit
from ...models.household import Household, HouseholdMember
from ...models.user import User
from .scope import membership_for

# Isolated on purpose. Do not fold this into TIER_USAGE_LIMITS.
HOUSEHOLD_CAP_MULTIPLIER = 1.5
SHARED_METER_MIN_MEMBERS = 2

@dataclass(frozen=True)
class UsageMeter:
    """Whose monthly row to charge, and how the cap is chosen."""

    user_id: int
    shared: bool
    uncapped: bool
    tier: str

    def limit_for(self, field: str) -> int | None:
        """Monthly cap for one usage field, or None when uncapped."""
        if self.uncapped:
            return None
        if self.shared:
            return shared_household_limit(field)
        return get_monthly_limit(self.tier, field)


def shared_household_limit(field: str) -> int | None:
    """Pro cap times ``HOUSEHOLD_CAP_MULTIPLIER``, rounded up.

    Returns None when the Pro tier does not cap that field. The base number
    is read from ``get_monthly_limit`` so this helper does not copy the table.
    """
    base = get_monthly_limit("pro", field)
    if base is None:
        return None
    return math.ceil(base * HOUSEHOLD_CAP_MULTIPLIER)


def resolve_usage_meter(session: Session, user: User) -> UsageMeter:
    """Resolve the meter for the signed-in user.

    Households with ``SHARED_METER_MIN_MEMBERS`` or more share the owner's
    row. Everyone else is charged on their own row at their own tier.
    """
    household, count = _household_size(session, user)
    if household is not None and count >= SHARED_METER_MIN_MEMBERS:
        owner = session.get(User, household.owner_user_id)
        return UsageMeter(
            user_id=household.owner_user_id,
            shared=True,
            uncapped=bool(owner is not None and owner.is_admin),
            tier="pro",
        )

    tier = "pro" if user.has_pro_access else "free"
    return UsageMeter(
        user_id=user.id,
        shared=False,
        uncapped=bool(user.is_admin),
        tier=tier,
    )


def _household_size(session: Session, user: User) -> tuple[Household | None, int]:
    member = membership_for(session, user.id)
    if member is None:
        return None, 0
    household = session.get(Household, member.household_id)
    if household is None:
        return None, 0
    count = session.scalar(
        select(func.count())
        .select_from(HouseholdMember)
        .where(HouseholdMember.household_id == household.id)
    )
    return household, int(count or 0)
