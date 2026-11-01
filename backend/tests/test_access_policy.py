"""Grandfathered free access ends 11:59 PM America/New_York on March 31, 2027."""

from datetime import datetime, timedelta, timezone

from app.core.access_policy import (
    ACCESS_FULL,
    ACCESS_READ_ONLY,
    at_or_before_plan_sunset,
    free_plan_sunset,
    resolve_access_mode,
)
from app.models.user import User


EXISTING = datetime(2026, 6, 1, tzinfo=timezone.utc)
NEW = datetime(2026, 11, 2, tzinfo=timezone.utc)


def test_default_sunset_is_1159_pm_eastern_not_utc():
    sunset = free_plan_sunset()
    assert sunset == datetime(2027, 4, 1, 3, 59, tzinfo=timezone.utc)
    assert sunset != datetime(2027, 3, 31, 23, 59, tzinfo=timezone.utc)


def test_existing_free_user_stays_full_through_the_eastern_instant():
    sunset = free_plan_sunset()
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=EXISTING,
            now=sunset,
        )
        == ACCESS_FULL
    )
    # Midnight UTC on April 1 is still 8:00 PM Eastern on March 31.
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=EXISTING,
            now=datetime(2027, 4, 1, 0, 0, tzinfo=timezone.utc),
        )
        == ACCESS_FULL
    )


def test_existing_free_user_is_read_only_after_the_eastern_instant():
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=EXISTING,
            now=free_plan_sunset() + timedelta(seconds=1),
        )
        == ACCESS_READ_ONLY
    )


def test_founding_offer_uses_the_same_instant():
    sunset = free_plan_sunset()
    assert at_or_before_plan_sunset(sunset) is True
    assert at_or_before_plan_sunset(sunset + timedelta(seconds=1)) is False


def test_accounts_created_after_the_cutoff_stay_on_the_free_plan():
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=NEW,
            now=free_plan_sunset() + timedelta(days=1),
        )
        == ACCESS_FULL
    )


def test_pro_and_admin_stay_full_after_the_deadline():
    later = free_plan_sunset() + timedelta(days=1)
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=True,
            created_at=EXISTING,
            now=later,
        )
        == ACCESS_FULL
    )
    assert (
        resolve_access_mode(
            is_admin=True,
            has_pro_access=False,
            created_at=EXISTING,
            now=later,
        )
        == ACCESS_FULL
    )


def test_user_property_matches_the_policy_before_the_deadline():
    user = User(
        clerk_id="clerk_existing",
        email="existing@example.com",
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
        created_at=EXISTING,
    )
    assert user.access_mode == ACCESS_FULL
    assert user.access_reason == "grandfathered_free"
    assert user.grandfathered_free_until == free_plan_sunset()


def test_store_subscription_grants_pro_without_stripe():
    user = User(
        clerk_id="clerk_store",
        email="store@example.com",
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
        store_provider="app_store",
        store_status="active",
        store_expires_at=datetime(2027, 12, 1, tzinfo=timezone.utc),
        created_at=EXISTING,
    )
    assert user.has_pro_access is True
    assert user.billing_channel == "app_store"
    assert user.access_reason == "store_subscription"
    assert user.access_mode == ACCESS_FULL
