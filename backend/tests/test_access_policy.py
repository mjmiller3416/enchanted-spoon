"""Grandfathered free access ends March 31, 2027; Pro never becomes read-only."""

from datetime import datetime, timezone

from app.core.access_policy import (
    ACCESS_FULL,
    ACCESS_READ_ONLY,
    resolve_access_mode,
)
from app.models.user import User


EXISTING = datetime(2026, 6, 1, tzinfo=timezone.utc)
NEW = datetime(2026, 11, 2, tzinfo=timezone.utc)
BEFORE_DEADLINE = datetime(2027, 3, 31, 12, 0, tzinfo=timezone.utc)
AFTER_DEADLINE = datetime(2027, 4, 1, 0, 0, tzinfo=timezone.utc)


def test_existing_free_user_stays_full_through_march_31_2027():
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=EXISTING,
            now=BEFORE_DEADLINE,
        )
        == ACCESS_FULL
    )


def test_existing_free_user_is_read_only_after_the_deadline():
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=EXISTING,
            now=AFTER_DEADLINE,
        )
        == ACCESS_READ_ONLY
    )


def test_accounts_created_after_the_cutoff_stay_on_the_free_plan():
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=False,
            created_at=NEW,
            now=AFTER_DEADLINE,
        )
        == ACCESS_FULL
    )


def test_pro_and_admin_stay_full_after_the_deadline():
    assert (
        resolve_access_mode(
            is_admin=False,
            has_pro_access=True,
            created_at=EXISTING,
            now=AFTER_DEADLINE,
        )
        == ACCESS_FULL
    )
    assert (
        resolve_access_mode(
            is_admin=True,
            has_pro_access=False,
            created_at=EXISTING,
            now=AFTER_DEADLINE,
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
    assert user.grandfathered_free_until is not None


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
