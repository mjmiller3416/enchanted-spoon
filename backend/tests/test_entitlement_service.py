"""Store entitlement decisions: one trial per account, Stripe left alone."""

from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.services.entitlement_service import (
    decide_revenuecat_event,
    decide_subscriber_snapshot,
)


def _user(**kwargs) -> User:
    user = User(
        clerk_id="clerk",
        email="person@example.com",
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
        **kwargs,
    )
    user.id = 7
    return user


def _event(**overrides):
    # Expiration is compared to the clock, so the window has to stay in the future.
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=7)
    payload = {
        "type": "INITIAL_PURCHASE",
        "app_user_id": "7",
        "store": "APP_STORE",
        "product_id": "com.enchantedspoon.app.pro.annual",
        "period_type": "TRIAL",
        "original_transaction_id": "tx_1",
        "expiration_at_ms": int(expires.timestamp() * 1000),
        "event_timestamp_ms": int(now.timestamp() * 1000),
        "environment": "SANDBOX",
    }
    payload.update(overrides)
    return payload


def test_app_store_trial_is_claimed():
    decision = decide_revenuecat_event(_user(), _event())
    assert decision.result == "applied"
    assert decision.updates["store_status"] == "trialing"
    assert decision.updates["store_provider"] == "app_store"
    assert decision.trial == ("app_store", "tx_1")


def test_play_store_uses_the_same_columns():
    decision = decide_revenuecat_event(_user(), _event(store="PLAY_STORE", period_type="NORMAL"))
    assert decision.updates["store_provider"] == "play_store"
    assert decision.updates["store_status"] == "active"
    assert decision.trial is None


def test_stripe_events_from_revenuecat_are_ignored():
    decision = decide_revenuecat_event(_user(), _event(store="STRIPE"))
    assert decision.result == "ignored"
    assert decision.updates == {}


def test_older_event_is_stale():
    user = _user(store_event_timestamp_ms=9_000)
    decision = decide_revenuecat_event(user, _event(event_timestamp_ms=8_000))
    assert decision.result == "stale"


def test_expiration_ends_access():
    decision = decide_revenuecat_event(_user(), _event(type="EXPIRATION", period_type="NORMAL"))
    assert decision.updates["store_status"] == "expired"
    assert decision.updates["store_will_renew"] is False
    assert decision.trial is None


def test_cancellation_keeps_access_until_expiry():
    decision = decide_revenuecat_event(
        _user(store_status="active"),
        _event(type="CANCELLATION", period_type="NORMAL"),
    )
    assert decision.updates["store_status"] == "active"
    assert decision.updates["store_will_renew"] is False


def test_snapshot_without_entitlement_expires_an_existing_store_plan():
    decision = decide_subscriber_snapshot(_user(store_status="active"), {"subscriber": {}})
    assert decision.updates["store_status"] == "expired"


def test_snapshot_trial_does_not_invent_a_transaction_id():
    future = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "subscriber": {
            "entitlements": {
                "pro": {
                    "product_identifier": "com.enchantedspoon.app.pro.monthly",
                    "expires_date": future,
                    "period_type": "trial",
                }
            },
            "subscriptions": {
                "com.enchantedspoon.app.pro.monthly": {
                    "store": "app_store",
                    "period_type": "trial",
                    "is_sandbox": True,
                }
            },
        }
    }
    decision = decide_subscriber_snapshot(_user(), payload)
    assert decision.updates["store_status"] == "trialing"
    assert decision.trial == ("app_store", None)


def test_claim_trial_allows_one_provider_only(db_session):
    from app.repositories.user_repo import UserRepo

    user = User(
        clerk_id="trial_user",
        email="trial@example.com",
        is_admin=False,
        subscription_tier="free",
    )
    db_session.add(user)
    db_session.flush()
    repo = UserRepo(db_session)

    assert repo.claim_trial(user, "app_store", "tx_1") is True
    assert repo.claim_trial(user, "app_store", "tx_1") is True
    assert repo.claim_trial(user, "stripe", "sub_1") is False
    assert repo.claim_trial(user, "app_store", "tx_2") is False
