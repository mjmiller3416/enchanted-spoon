"""Tests for StripeWebhookService — signature verification and subscription sync.

Covers:
- Signature verification: missing secret, missing header, invalid signature, happy path
- checkout.session.completed: resolves user via client_reference_id, falls back to
  customer id, skips unknown users without raising
- invoice.paid: keeps a paying user active
- customer.subscription.updated: tier follows Stripe status
- customer.subscription.deleted: downgrades to free
- Unhandled event types are ignored
- DB errors roll back and raise StripeWebhookProcessingError
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import stripe
from sqlalchemy.exc import SQLAlchemyError

from app.core.stripe_config import StripeSettings
from app.models.user import User
from app.services.stripe_webhook_service import (
    InvalidStripeSignatureError,
    StripeWebhookProcessingError,
    StripeWebhookService,
)


def _service_with_mock_repo():
    """Build a StripeWebhookService backed by a MagicMock session and repo."""
    session = MagicMock()
    service = StripeWebhookService(session)
    service.repo = MagicMock()
    return service, session


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

class TestVerifyAndParseEvent:
    def test_missing_secret_raises(self):
        service, _ = _service_with_mock_repo()
        settings = StripeSettings(stripe_webhook_secret=None)

        with pytest.raises(InvalidStripeSignatureError):
            service.verify_and_parse_event(b"{}", "sig", settings)

    def test_missing_signature_header_raises(self):
        service, _ = _service_with_mock_repo()
        settings = StripeSettings(stripe_webhook_secret="whsec_test")

        with pytest.raises(InvalidStripeSignatureError):
            service.verify_and_parse_event(b"{}", None, settings)

    def test_invalid_signature_raises(self):
        service, _ = _service_with_mock_repo()
        settings = StripeSettings(stripe_webhook_secret="whsec_test")

        with patch(
            "app.services.stripe_webhook_service.stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad sig", "sig_header"),
        ):
            with pytest.raises(InvalidStripeSignatureError):
                service.verify_and_parse_event(b"{}", "bad-sig", settings)

    def test_valid_signature_returns_parsed_event(self):
        service, _ = _service_with_mock_repo()
        settings = StripeSettings(stripe_webhook_secret="whsec_test")
        fake_event = {"type": "checkout.session.completed"}

        with patch(
            "app.services.stripe_webhook_service.stripe.Webhook.construct_event",
            return_value=fake_event,
        ) as mock_construct:
            result = service.verify_and_parse_event(b"{}", "good-sig", settings)

        assert result == fake_event
        mock_construct.assert_called_once_with(b"{}", "good-sig", "whsec_test")


# ---------------------------------------------------------------------------
# checkout.session.completed
# ---------------------------------------------------------------------------

class TestHandleEventCheckoutCompleted:
    def test_resolves_user_via_client_reference_id(self):
        service, session = _service_with_mock_repo()
        user = User(id=1)
        service.repo.get_by_id.return_value = user

        event = {
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_123", "client_reference_id": "1"}},
        }
        service.handle_event(event)

        service.repo.get_by_id.assert_called_once_with(1)
        service.repo.update_subscription.assert_called_once_with(
            user,
            stripe_customer_id="cus_123",
            subscription_tier="pro",
            subscription_status="active",
        )
        session.commit.assert_called_once()

    def test_falls_back_to_customer_id_when_no_reference(self):
        service, session = _service_with_mock_repo()
        user = User(id=2)
        service.repo.get_by_id.return_value = None
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_456", "client_reference_id": None}},
        }
        service.handle_event(event)

        service.repo.get_by_stripe_customer_id.assert_called_once_with("cus_456")
        service.repo.update_subscription.assert_called_once()

    def test_unknown_user_is_skipped_without_raising(self):
        service, session = _service_with_mock_repo()
        service.repo.get_by_id.return_value = None
        service.repo.get_by_stripe_customer_id.return_value = None

        event = {
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_789", "client_reference_id": "999"}},
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_not_called()
        session.commit.assert_called_once()

    def test_unpaid_checkout_records_customer_but_defers_pro(self):
        service, session = _service_with_mock_repo()
        user = User(id=7)
        service.repo.get_by_id.return_value = user

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_delayed",
                    "client_reference_id": "7",
                    "payment_status": "unpaid",
                }
            },
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user, stripe_customer_id="cus_delayed"
        )
        session.commit.assert_called_once()

    def test_no_payment_required_checkout_grants_pro(self):
        service, session = _service_with_mock_repo()
        user = User(id=8)
        service.repo.get_by_id.return_value = user

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_trial",
                    "client_reference_id": "8",
                    "payment_status": "no_payment_required",
                }
            },
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            stripe_customer_id="cus_trial",
            subscription_tier="pro",
            subscription_status="active",
        )


# ---------------------------------------------------------------------------
# invoice.paid
# ---------------------------------------------------------------------------

class TestHandleEventInvoicePaid:
    def test_marks_user_active_pro(self):
        service, session = _service_with_mock_repo()
        user = User(id=3)
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {"type": "invoice.paid", "data": {"object": {"customer": "cus_abc"}}}
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user, subscription_tier="pro", subscription_status="active"
        )
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# customer.subscription.updated
# ---------------------------------------------------------------------------

class TestHandleEventSubscriptionUpdated:
    @pytest.mark.parametrize(
        "status,expected_tier",
        [
            ("active", "pro"),
            ("trialing", "pro"),
            ("past_due", "pro"),
            ("canceled", "free"),
            ("unpaid", "free"),
            ("incomplete_expired", "free"),
        ],
    )
    def test_tier_follows_stripe_status(self, status, expected_tier):
        service, session = _service_with_mock_repo()
        user = User(id=4)
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_xyz",
                    "status": status,
                    "current_period_end": 1700000000,
                }
            },
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            subscription_tier=expected_tier,
            subscription_status=status,
            subscription_ends_at=datetime.fromtimestamp(1700000000, tz=timezone.utc),
            cancel_at_period_end=False,
        )

    def test_cancel_at_period_end_passes_through(self):
        # A portal cancel keeps status=active but sets cancel_at_period_end —
        # the flag is what lets the UI say "ends on X" instead of "renews on X".
        service, session = _service_with_mock_repo()
        user = User(id=12)
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_cancel",
                    "status": "active",
                    "current_period_end": 1700000000,
                    "cancel_at_period_end": True,
                }
            },
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            subscription_tier="pro",
            subscription_status="active",
            subscription_ends_at=datetime.fromtimestamp(1700000000, tz=timezone.utc),
            cancel_at_period_end=True,
        )

    def test_created_event_populates_period_end_for_new_subscriber(self):
        # customer.subscription.created shares the updated handler so a brand-new
        # subscriber gets subscription_ends_at immediately (checkout.session.completed
        # carries no period end).
        service, session = _service_with_mock_repo()
        user = User(id=11)
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "customer": "cus_new",
                    "status": "active",
                    "current_period_end": 1900000000,
                }
            },
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            subscription_tier="pro",
            subscription_status="active",
            subscription_ends_at=datetime.fromtimestamp(1900000000, tz=timezone.utc),
            cancel_at_period_end=False,
        )
        session.commit.assert_called_once()

    def test_period_end_falls_back_to_subscription_items(self):
        # Stripe API 2025-03-31+ ("basil") reports current_period_end on
        # subscription items, not on the subscription object itself.
        service, session = _service_with_mock_repo()
        user = User(id=9)
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_basil",
                    "status": "active",
                    "items": {"data": [{"current_period_end": 1800000000}]},
                }
            },
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            subscription_tier="pro",
            subscription_status="active",
            subscription_ends_at=datetime.fromtimestamp(1800000000, tz=timezone.utc),
            cancel_at_period_end=False,
        )


# ---------------------------------------------------------------------------
# customer.subscription.deleted
# ---------------------------------------------------------------------------

class TestHandleEventSubscriptionDeleted:
    def test_downgrades_to_free_canceled(self):
        service, session = _service_with_mock_repo()
        user = User(id=5)
        service.repo.get_by_stripe_customer_id.return_value = user

        event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_del", "ended_at": 1700000000}},
        }
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            subscription_tier="free",
            subscription_status="canceled",
            subscription_ends_at=datetime.fromtimestamp(1700000000, tz=timezone.utc),
            cancel_at_period_end=False,
        )


# ---------------------------------------------------------------------------
# Unhandled event types & error handling
# ---------------------------------------------------------------------------

class TestHandleEventUnhandledType:
    def test_ignored_without_touching_repo_or_committing(self):
        service, session = _service_with_mock_repo()

        service.handle_event({"type": "customer.created", "data": {"object": {}}})

        service.repo.update_subscription.assert_not_called()
        session.commit.assert_not_called()


class TestHandleEventDbError:
    def test_rolls_back_and_raises_processing_error(self):
        service, session = _service_with_mock_repo()
        user = User(id=6)
        service.repo.get_by_stripe_customer_id.return_value = user
        session.commit.side_effect = SQLAlchemyError("boom")

        event = {"type": "invoice.paid", "data": {"object": {"customer": "cus_err"}}}

        with pytest.raises(StripeWebhookProcessingError):
            service.handle_event(event)

        session.rollback.assert_called_once()


class TestHandleEventStripeObject:
    def test_real_stripe_event_object_is_converted_to_dict(self):
        # Regression: stripe-python's StripeObject (what construct_event
        # actually yields for data.object) lacks Mapping methods like .get();
        # handle_event must convert it before the handlers touch it.
        service, session = _service_with_mock_repo()
        user = User(id=10)
        service.repo.get_by_id.return_value = user

        event = stripe.Event.construct_from(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer": "cus_real",
                        "client_reference_id": "10",
                        "payment_status": "paid",
                    }
                },
            },
            "sk_test_dummy",
        )
        service.handle_event(event)

        service.repo.update_subscription.assert_called_once_with(
            user,
            stripe_customer_id="cus_real",
            subscription_tier="pro",
            subscription_status="active",
        )
        session.commit.assert_called_once()
