"""Production checkout must fail before creating customers if billing is not live."""
from unittest.mock import MagicMock, patch
import pytest
from app.core.stripe_config import StripeSettings
from app.services.billing_service import BillingService, StripeNotConfiguredError

@pytest.mark.parametrize("key, webhook, url", [
    ("sk_test_dummy", "whsec_dummy", "https://example.com"),
    ("sk_live_dummy", None, "https://example.com"),
    ("sk_live_dummy", "whsec_dummy", "http://localhost:3000"),
])
def test_incomplete_production_checkout_never_calls_stripe(monkeypatch, key, webhook, url):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    settings = StripeSettings(_env_file=None, stripe_secret_key=key, stripe_webhook_secret=webhook,
                              stripe_price_id_pro="price_test", frontend_url=url)
    service = BillingService(MagicMock(), settings=settings)
    with patch.object(service, "get_or_create_customer") as customer, patch("stripe.checkout.Session.create") as checkout:
        with pytest.raises(StripeNotConfiguredError):
            service.create_checkout_session(MagicMock())
        customer.assert_not_called()
        checkout.assert_not_called()


@pytest.mark.parametrize("livemode,accepted", [(True, True), (False, False), (None, False)])
def test_production_verifies_real_signed_events(monkeypatch, livemode, accepted):
    import hashlib
    import hmac
    import json
    import time
    import stripe
    from app.services.stripe_webhook_service import StripeWebhookService, InvalidStripeSignatureError
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    secret = "whsec_synthetic_test_only"
    settings = StripeSettings(_env_file=None, stripe_webhook_secret=secret)
    data = {"id": "evt_synthetic", "object": "event", "type": "synthetic.unhandled", "data": {"object": {}}}
    if livemode is not None:
        data["livemode"] = livemode
    payload = json.dumps(data).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
    signature = f"t={timestamp},v1={digest}"
    service = StripeWebhookService(MagicMock())
    if accepted:
        event = service.verify_and_parse_event(payload, signature, settings)
        assert isinstance(event, stripe.Event)
        assert event["livemode"] is True
        service.handle_event(event)
    else:
        with pytest.raises(InvalidStripeSignatureError):
            service.verify_and_parse_event(payload, signature, settings)
