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

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.usage_limits import (
    HOUSEHOLD_PRO_CAP_MULTIPLIER,
    get_monthly_limit,
    scale_cap,
    set_household_usage_hooks,
)
from ...models.household import Household, HouseholdMember
from ...models.user import User
from .scope import membership_for

# Same number #210 exposes. The request path applies it through the hook.
HOUSEHOLD_CAP_MULTIPLIER = HOUSEHOLD_PRO_CAP_MULTIPLIER
SHARED_METER_MIN_MEMBERS = 2

_meter_session: ContextVar[Session | None] = ContextVar(
    "household_meter_session", default=None
)

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
    """Pro cap times ``HOUSEHOLD_PRO_CAP_MULTIPLIER``, rounded up.

    This is the number ``usage_meter`` returns for a Pro owner once the
    household hook is bound and the household has two or more members.
    """
    return scale_cap(get_monthly_limit("pro", field), HOUSEHOLD_PRO_CAP_MULTIPLIER)


@contextmanager
def bind_household_meter(session: Session):
    """Let the usage hooks see this request's session."""
    token = _meter_session.set(session)
    try:
        yield
    finally:
        _meter_session.reset(token)


def household_usage_subject(user: User) -> User:
    """Owner when two or more people share a household, otherwise ``user``."""
    session = _meter_session.get()
    if session is None:
        return user
    meter = resolve_usage_meter(session, user)
    if not meter.shared:
        return user
    owner = session.get(User, meter.user_id)
    return owner if owner is not None else user


def household_usage_multiplier(user: User) -> float:
    """1.5 for a pooled owner, 1.0 otherwise.

    ``usage_limits`` calls this with the subject. It scales Pro caps only.
    """
    session = _meter_session.get()
    if session is None:
        return 1.0
    meter = resolve_usage_meter(session, user)
    if meter.shared:
        return HOUSEHOLD_PRO_CAP_MULTIPLIER
    return 1.0


def install_household_usage_hooks() -> None:
    """Register this module with #210's usage hook."""
    set_household_usage_hooks(
        subject=household_usage_subject,
        multiplier=household_usage_multiplier,
    )


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
