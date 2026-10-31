"""Billing lifecycle uses real transactions and synthetic Stripe 16 snapshot fixtures."""
import hashlib
import hmac
import json
import logging
import time
from unittest.mock import patch

import pytest
import stripe
from sqlalchemy.exc import SQLAlchemyError

from app.core.stripe_config import STRIPE_API_VERSION, StripeSettings
from app.models import BillingEvent, User
from app.services.stripe_webhook_service import (
    HANDLED_EVENT_TYPES, REVIEW_EVENT_TYPES, InvalidStripeSignatureError,
    StripeWebhookProcessingError, StripeWebhookService,
)


@pytest.fixture
def billing(file_db):
    with file_db() as session:
        user = session.get(User, 1)
        user.is_admin = False
        user.stripe_customer_id = "cus_synthetic"
        user.subscription_tier = "free"
        user.subscription_status = "active"
        session.commit()
        settings = StripeSettings(_env_file=None, stripe_secret_key="sk_test_synthetic",
            stripe_price_id_pro="price_pro", stripe_webhook_secret="whsec_synthetic")
        yield StripeWebhookService(session, settings), user


def snapshot(kind="customer.subscription.updated", event_id="evt_synthetic", **overrides):
    data = {"customer": "cus_synthetic", "mode": "subscription", "client_reference_id": "1"}
    data.update(overrides)
    return {"id": event_id, "object": "event", "type": kind, "created": 1900000000,
            "api_version": STRIPE_API_VERSION, "livemode": False, "data": {"object": data}}


def subscription(status="active", paid=True, **overrides):
    data = {"id": "sub_synthetic", "customer": "cus_synthetic", "status": status,
            "created": 1900000000, "cancel_at_period_end": False,
            "latest_invoice": {"id": "in_synthetic", "paid": paid, "status": "paid" if paid else "open"},
            "items": {"data": [{"price": {"id": "price_pro"}, "current_period_end": 2000000000}]}}
    data.update(overrides)
    return data


def current(*subscriptions, has_more=False):
    return stripe.ListObject.construct_from({"object": "list", "data": list(subscriptions), "has_more": has_more}, "sk_test_synthetic")


def signed(data, secret="whsec_synthetic"):
    payload = json.dumps(data).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
    return payload, f"t={timestamp},v1={digest}"


def test_sdk_and_fixture_versions_are_pinned():
    from pathlib import Path
    assert stripe.VERSION == "16.0.0"
    assert STRIPE_API_VERSION == "2026-09-30.endive"
    assert "stripe==16.0.0" in (Path(__file__).resolve().parents[1] / "requirements.txt").read_text()


@pytest.mark.parametrize("invalid", ["signature", "secret", "version", "mode", "missing_signature"])
def test_real_signed_snapshot_validation(billing, invalid):
    service, _ = billing
    event = snapshot()
    if invalid == "version":
        event["api_version"] = "2020-08-27"
    if invalid == "mode":
        event["livemode"] = True
    body, header = signed(event, "different_secret" if invalid == "secret" else "whsec_synthetic")
    if invalid == "signature":
        header = "invalid"
    if invalid == "missing_signature":
        header = None
    with pytest.raises(InvalidStripeSignatureError):
        service.verify_and_parse_event(body, header, service.settings)


def test_signed_real_sdk_event_reconciles_and_duplicate_does_not_fetch_again(billing):
    service, user = billing
    body, header = signed(snapshot("checkout.session.completed", payment_status="paid"))
    event = service.verify_and_parse_event(body, header, service.settings)
    with patch("stripe.Subscription.list", return_value=current(subscription())) as fetch:
        service.handle_event(event)
        service.handle_event(event)
        fetch.assert_called_once()
        assert fetch.call_args.kwargs["stripe_version"] == STRIPE_API_VERSION
    assert user.has_pro_access
    assert service.session.get(BillingEvent, "evt_synthetic").outcome == "reconciled"
    assert user.subscription_ends_at.year == 2033


@pytest.mark.parametrize("kind", sorted(HANDLED_EVENT_TYPES - REVIEW_EVENT_TYPES))
def test_all_billing_wakeups_use_current_subscription_not_event_snapshot(billing, kind):
    service, user = billing
    with patch("stripe.Subscription.list", return_value=current(subscription())):
        service.handle_event(snapshot(kind, status="canceled", payment_status="unpaid"))
    assert user.subscription_status == "active"
    assert user.has_pro_access


@pytest.mark.parametrize("status,expected", [("active", True), ("trialing", True),
    ("canceled", False), ("unpaid", False), ("incomplete_expired", False)])
def test_authoritative_status_and_period_end(billing, status, expected):
    service, user = billing
    user.subscription_tier = "pro"
    service.session.commit()
    with patch("stripe.Subscription.list", return_value=current(subscription(status, cancel_at_period_end=True))):
        service.handle_event(snapshot())
    assert user.has_pro_access is expected
    assert user.subscription_status == status
    assert user.cancel_at_period_end is True


@pytest.mark.parametrize("existing_pro", [False, True])
def test_failed_renewal_preserves_existing_access_without_granting_unpaid_access(billing, existing_pro):
    service, user = billing
    user.subscription_tier = "pro" if existing_pro else "free"
    service.session.commit()
    with patch("stripe.Subscription.list", return_value=current(subscription("past_due", paid=False))):
        service.handle_event(snapshot("invoice.payment_failed"))
    assert user.has_pro_access is existing_pro


@pytest.mark.parametrize("status", ["active", "incomplete", "unknown_future_status", "paused"])
def test_unsettled_or_unknown_state_never_grants_new_access(billing, status):
    service, user = billing
    with patch("stripe.Subscription.list", return_value=current(subscription(status, paid=False))):
        service.handle_event(snapshot("checkout.session.async_payment_failed"))
    assert not user.has_pro_access
    assert service.session.get(BillingEvent, "evt_synthetic").outcome.startswith("review_")


def test_delayed_payment_grants_only_after_authoritative_settlement(billing):
    service, user = billing
    with patch("stripe.Subscription.list", return_value=current(subscription("incomplete", paid=False))):
        service.handle_event(snapshot("checkout.session.completed", "evt_unpaid", payment_status="unpaid"))
    assert not user.has_pro_access
    with patch("stripe.Subscription.list", return_value=current(subscription())):
        service.handle_event(snapshot("checkout.session.async_payment_succeeded", "evt_paid"))
    assert user.has_pro_access


def test_late_invoice_paid_does_not_revive_canceled_subscription(billing):
    service, user = billing
    with patch("stripe.Subscription.list", return_value=current(subscription("canceled"))):
        service.handle_event(snapshot("customer.subscription.deleted", "evt_deleted"))
        service.handle_event(snapshot("invoice.paid", "evt_old_paid", status="active"))
    assert not user.has_pro_access
    assert user.subscription_status == "canceled"


def test_old_subscription_deletion_does_not_revoke_new_paid_subscription(billing):
    service, user = billing
    with patch("stripe.Subscription.list", return_value=current(subscription("canceled"), subscription(id="sub_new"))):
        service.handle_event(snapshot("customer.subscription.deleted"))
    assert user.has_pro_access


def test_reference_id_for_someone_elses_customer_is_not_trusted(billing):
    service, user = billing
    victim = User(clerk_id="victim", email="victim@example.test", stripe_customer_id="cus_victim")
    service.session.add(victim)
    service.session.commit()
    with patch("stripe.Subscription.list", return_value=current(subscription())):
        service.handle_event(snapshot("checkout.session.completed", client_reference_id=str(victim.id)))
    assert user.has_pro_access
    assert not victim.has_pro_access


@pytest.mark.parametrize("mode", ["payment", None])
def test_one_off_or_unknown_checkout_mode_does_not_grant_pro(billing, mode):
    service, user = billing
    with patch("stripe.Subscription.list") as fetch:
        service.handle_event(snapshot("checkout.session.completed", mode=mode))
        fetch.assert_not_called()
    assert not user.has_pro_access


def test_unknown_customer_is_reviewed_without_claiming_reference_id(billing):
    service, user = billing
    with patch("stripe.Subscription.list") as fetch:
        service.handle_event(snapshot("checkout.session.completed", customer="cus_unmapped", client_reference_id=str(user.id)))
        fetch.assert_not_called()
    assert not user.has_pro_access
    assert service.session.get(BillingEvent, "evt_synthetic").outcome == "review_unknown_customer"


def test_other_price_preserves_existing_entitlement_for_review(billing):
    service, user = billing
    user.subscription_tier = "pro"
    service.session.commit()
    other = subscription(items={"data": [{"price": {"id": "price_other"}}]})
    with patch("stripe.Subscription.list", return_value=current(other)):
        service.handle_event(snapshot())
    assert user.has_pro_access
    assert service.session.get(BillingEvent, "evt_synthetic").outcome == "review_unmatched_price"


@pytest.mark.parametrize("kind", sorted(REVIEW_EVENT_TYPES))
def test_refund_dispute_fraud_are_private_review_only(billing, caplog, kind):
    service, user = billing
    user.subscription_tier = "pro"
    service.session.commit()
    marker = "synthetic-private-payload"
    with patch("stripe.Subscription.list") as fetch:
        service.handle_event(snapshot(kind, customer=marker, description=marker))
        fetch.assert_not_called()
    assert user.has_pro_access
    receipt = service.session.get(BillingEvent, "evt_synthetic")
    assert receipt.outcome == "review_required"
    assert marker not in repr(receipt.__dict__)
    assert marker not in caplog.text


@pytest.mark.parametrize("failure", [stripe.APIConnectionError("synthetic-sensitive-provider-detail"), SQLAlchemyError("synthetic-sensitive-provider-detail")])
def test_failure_rolls_back_and_retry_preserves_access(billing, caplog, failure):
    service, user = billing
    user.subscription_tier = "pro"
    service.session.commit()
    with patch("stripe.Subscription.list", side_effect=failure):
        with pytest.raises(StripeWebhookProcessingError) as caught:
            service.handle_event(snapshot())
    assert caught.value.__context__ is None
    assert "synthetic-sensitive" not in str(caught.value)
    assert "synthetic-sensitive" not in caplog.text
    assert user.has_pro_access
    assert service.session.get(BillingEvent, "evt_synthetic") is None
    with patch("stripe.Subscription.list", return_value=current(subscription())):
        service.handle_event(snapshot())
    assert service.session.get(BillingEvent, "evt_synthetic") is not None


def test_truncated_state_cannot_revoke_access(billing):
    service, user = billing
    user.subscription_tier = "pro"
    service.session.commit()
    with patch("stripe.Subscription.list", return_value=current(subscription("canceled"), has_more=True)):
        with pytest.raises(StripeWebhookProcessingError):
            service.handle_event(snapshot())
    assert user.has_pro_access


def test_unhandled_event_does_not_call_stripe_or_store_receipt(billing):
    service, _ = billing
    with patch("stripe.Subscription.list") as fetch:
        service.handle_event(snapshot("customer.created"))
        fetch.assert_not_called()
    assert service.session.get(BillingEvent, "evt_synthetic") is None


def test_commit_failure_rolls_back_entitlement_and_receipt_together(billing):
    service, user = billing
    user.subscription_tier = "pro"
    service.session.commit()
    with patch("stripe.Subscription.list", return_value=current(subscription("canceled"))), \
         patch.object(service.session, "commit", side_effect=SQLAlchemyError("synthetic failure")):
        with pytest.raises(StripeWebhookProcessingError):
            service.handle_event(snapshot())
    service.session.refresh(user)
    assert user.has_pro_access
    assert service.session.get(BillingEvent, "evt_synthetic") is None


def test_duplicate_receipt_survives_new_database_session(billing, file_db):
    service, _ = billing
    with patch("stripe.Subscription.list", return_value=current(subscription())):
        service.handle_event(snapshot())
    with file_db() as fresh_session, patch("stripe.Subscription.list") as fetch:
        StripeWebhookService(fresh_session, service.settings).handle_event(snapshot())
        fetch.assert_not_called()


def test_missing_webhook_secret_and_event_id_are_rejected(billing):
    service, _ = billing
    settings = service.settings.model_copy(update={"stripe_webhook_secret": None})
    with pytest.raises(InvalidStripeSignatureError):
        service.verify_and_parse_event(b"{}", "sig", settings)
    data = snapshot()
    del data["id"]
    with pytest.raises(StripeWebhookProcessingError):
        service.handle_event(data)


def test_billing_ledger_migration_preserves_existing_users(tmp_path, monkeypatch):
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text, inspect
    backend = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{tmp_path / 'billing-migration.db'}"
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", url)
    monkeypatch.chdir(backend)
    config = Config(str(backend / "alembic.ini"))
    command.upgrade(config, "f5b0d3e8c2a4")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (clerk_id,email,is_admin,subscription_tier,subscription_status,cancel_at_period_end,created_at,updated_at) VALUES ('existing','existing@example.test',0,'pro','active',0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(config, "head")
    assert "billing_events" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT subscription_tier, usage_plan FROM users WHERE clerk_id='existing'")).one() == ("pro", "legacy")
        assert connection.execute(text("SELECT COUNT(*) FROM billing_events")).scalar() == 0
    engine.dispose()


def test_signed_webhook_route_reconciles_even_while_checkout_disabled(billing):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.stripe_webhooks import router
    from app.database.db import get_session
    from app.core.stripe_config import get_stripe_settings
    service, user = billing
    app = FastAPI()
    app.include_router(router, prefix="/api/webhooks/stripe")
    app.dependency_overrides[get_session] = lambda: service.session
    app.dependency_overrides[get_stripe_settings] = lambda: service.settings
    assert service.settings.stripe_checkout_enabled is False
    body, header = signed(snapshot())
    with patch("stripe.Subscription.list", return_value=current(subscription())):
        response = TestClient(app).post("/api/webhooks/stripe", content=body,
            headers={"Stripe-Signature": header, "Content-Type": "application/json"})
    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert user.has_pro_access
