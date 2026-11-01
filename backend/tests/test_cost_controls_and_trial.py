"""Cost controls, trial billing, founder codes, and the free-plan sunset.

Stripe calls in this file are mocks. There are no test-mode keys in this
environment, so the $0-invoice / first_time_transaction question is NOT
verified against Stripe. See docs/stripe-test-clock-founder-promo.md.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.api.ai.image_generation import router as image_router
from app.api.auth import get_current_user
from app.api.recipes import router as recipe_router
from app.api.read_only import reject_read_only_writes
from app.core.rate_limit import enforce_pre_quota_limits, limiter
from app.core.stripe_config import STRIPE_TRIAL_DAYS, StripeSettings
from app.core.usage_limits import TRIAL_USAGE_WINDOW, get_user_monthly_limit
from app.database.db import get_session
from app.models.user import User
from app.models.user_usage import UserUsage
from app.services.billing_service import BillingService
from app.services.founder_codes import PromotionCodeRejected, lookup_founder_promotion
from app.services.free_tier_sunset import apply_free_tier_sunset, due_reminder_kind
from app.services.usage_service import UsageService
from fastapi import Depends


def _user(**overrides) -> User:
    values = dict(
        id=1,
        clerk_id="clerk",
        email="cook@example.test",
        is_admin=False,
        usage_plan="launch",
        subscription_tier="free",
        subscription_status="active",
        has_used_trial=False,
        cancel_at_period_end=False,
    )
    values.update(overrides)
    return User(**values)


def _promo(code_id="promo_test", coupon="FOUNDER30_MONTHLY", redeemed=0, maximum=70):
    return SimpleNamespace(to_dict=lambda: {"data": [{
        "id": code_id,
        "active": True,
        "times_redeemed": redeemed,
        "max_redemptions": maximum,
        "coupon": {"id": coupon},
        "restrictions": {"first_time_transaction": True},
    }]})


def _settings(**overrides) -> StripeSettings:
    values = dict(
        _env_file=None,
        stripe_checkout_enabled=True,
        stripe_secret_key="sk_test_synthetic",
        stripe_webhook_secret="whsec_synthetic",
        stripe_price_id_pro="price_legacy",
        stripe_price_pro_monthly_v2="price_month_v2",
        stripe_price_pro_annual_v2="price_year_v2",
        frontend_url="http://localhost:3000",
    )
    values.update(overrides)
    return StripeSettings(**values)


def test_launch_trial_and_expired_caps():
    pro = _user(subscription_tier="pro", subscription_status="active")
    assert get_user_monthly_limit(pro, "ai_images_generated") == 20
    assert get_user_monthly_limit(pro, "ai_assistant_messages") == 300
    assert get_user_monthly_limit(pro, "ai_suggestions_requested") == 200
    assert get_user_monthly_limit(pro, "recipes_imported") == 50

    trial = _user(subscription_tier="pro", subscription_status="trialing")
    assert trial.usage_tier == "trial"
    assert trial.access_reason == "trial"
    assert trial.has_pro_access is True
    assert get_user_monthly_limit(trial, "ai_images_generated") == 3
    assert get_user_monthly_limit(trial, "ai_assistant_messages") == 25

    ended = _user(
        subscription_tier="pro",
        subscription_status="trialing",
        trial_ends_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert ended.usage_tier == "expired"
    assert get_user_monthly_limit(ended, "ai_images_generated") == 0

    admin = _user(is_admin=True)
    assert get_user_monthly_limit(admin, "ai_images_generated") is None
    granted = _user(granted_pro_until=datetime.now(timezone.utc) + timedelta(days=1))
    assert granted.usage_tier == "pro"


def test_trial_usage_does_not_reset_on_a_new_calendar_month(file_db):
    with file_db() as session:
        user = session.get(User, 1)
        user.subscription_tier = "pro"
        user.subscription_status = "trialing"
        user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=3)
        session.commit()
        service = UsageService(session, user.id, window=TRIAL_USAGE_WINDOW)
        service.reserve("ai_assistant_messages", 25)
        session.expire_all()
        stored = session.query(UserUsage).filter_by(user_id=1, month=TRIAL_USAGE_WINDOW).one()
        assert stored.ai_assistant_messages == 1
        assert session.query(UserUsage).filter(UserUsage.month != TRIAL_USAGE_WINDOW).count() == 0


def test_checkout_attaches_trial_tax_and_first_time_promo_before_any_invoice():
    """UNVERIFIED against Stripe.

    A first checkout has no invoices yet, so we attach FOUNDER30 together with
    the 7-day trial. Whether Stripe's first_time_transaction later treats the
    $0 trial invoice as a transaction is not proven here.
    """
    user = _user(stripe_customer_id=None)
    service = BillingService(MagicMock(), settings=_settings())
    service.session.execute.return_value.rowcount = 1
    with patch.object(service, "get_or_create_customer", return_value="cus_new") as customer, \
         patch("app.services.founder_codes.stripe.PromotionCode.list", return_value=_promo()), \
         patch("stripe.checkout.Session.create", return_value=MagicMock(id="cs_trial", url="https://pay.test/c")) as create:
        assert service.create_checkout_session(user, plan="monthly", promotion_code=" founder30 ") == "https://pay.test/c"
    customer.assert_called_once()
    params = create.call_args.kwargs
    assert params["line_items"] == [{"price": "price_month_v2", "quantity": 1}]
    assert params["subscription_data"]["trial_period_days"] == STRIPE_TRIAL_DAYS
    assert params["subscription_data"]["trial_settings"] == {
        "end_behavior": {"missing_payment_method": "cancel"}
    }
    assert params["discounts"] == [{"promotion_code": "promo_test"}]
    assert params["automatic_tax"] == {"enabled": True}
    assert "allow_promotion_codes" not in params
    assert params.get("payment_method_collection") != "if_required"
    assert "payment_method_collection" not in params


def test_monthly_price_falls_back_when_v2_is_unset():
    user = _user()
    service = BillingService(MagicMock(), settings=_settings(stripe_price_pro_monthly_v2=None))
    with patch.object(service, "get_or_create_customer", return_value="cus_new"), \
         patch("stripe.checkout.Session.create", return_value=MagicMock(url="https://pay.test/c")) as create:
        service.create_checkout_session(user, plan="monthly")
    assert create.call_args.kwargs["line_items"][0]["price"] == "price_legacy"


def test_second_checkout_omits_the_trial():
    user = _user(has_used_trial=True)
    service = BillingService(MagicMock(), settings=_settings())
    with patch.object(service, "get_or_create_customer", return_value="cus_new"), \
         patch("stripe.checkout.Session.create", return_value=MagicMock(url="https://pay.test/c")) as create:
        service.create_checkout_session(user, plan="annual")
    assert "trial_period_days" not in create.call_args.kwargs.get("subscription_data", {})
    assert create.call_args.kwargs["line_items"][0]["price"] == "price_year_v2"


def test_founder_code_must_match_the_plan():
    with pytest.raises(PromotionCodeRejected):
        lookup_founder_promotion("FOUNDER30", "annual")
    with pytest.raises(PromotionCodeRejected):
        lookup_founder_promotion("FOUNDER30Y", "monthly")


def test_zero_dollar_invoice_customer_is_not_reused_for_a_later_checkout():
    """A later checkout does not reuse a customer that already has an invoice.

    The new customer has no invoices, which is what a first_time_transaction
    restriction can evaluate. This does not prove Stripe's treatment of the
    $0 invoice created after the original trial signup.
    """
    user = _user(stripe_customer_id="cus_old", has_used_trial=True)
    service = BillingService(MagicMock(), settings=_settings())
    service.repo = MagicMock()
    invoice = SimpleNamespace(data=[SimpleNamespace(id="in_zero", amount_paid=0, total=0)])
    with patch("stripe.Invoice.list", return_value=invoice) as listed, \
         patch("stripe.Customer.create", return_value=SimpleNamespace(id="cus_fresh")) as created, \
         patch("stripe.checkout.Session.create", return_value=MagicMock(url="https://pay.test/c")) as create:
        service.create_checkout_session(user, plan="monthly")
    listed.assert_called_once()
    created.assert_called_once()
    assert create.call_args.kwargs["customer"] == "cus_fresh"
    assert "discounts" not in create.call_args.kwargs


def test_image_client_does_not_retry_http_500(monkeypatch):
    monkeypatch.setenv("GEMINI_IMAGE_API_KEY", "test-key")
    from app.services.ai.gemini_client import clear_gemini_clients, get_gemini_client
    clear_gemini_clients()
    client = get_gemini_client("GEMINI_IMAGE_API_KEY", retry_attempts=1, timeout_ms=120_000)
    options = client._api_client._http_options
    assert options.timeout == 120_000
    assert options.retry_options.attempts == 1
    assert 500 not in options.retry_options.http_status_codes
    assert options.retry_options.http_status_codes == [429, 503]


def test_image_500_tries_the_fallback_model_once(monkeypatch):
    from app.services.ai.image_generation.service import ImageGenerationService
    from app.services.ai import image_generation as image_pkg
    calls = []

    async def generate_content(**kwargs):
        calls.append((kwargs["model"], kwargs["config"].image_config.image_size))
        if kwargs["model"].endswith("lite-image"):
            raise RuntimeError("simulated 500")
        return MagicMock()

    client = MagicMock()
    client.aio.models.generate_content = generate_content
    monkeypatch.setattr(image_pkg.service, "get_gemini_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(image_pkg.service, "extract_image_data", lambda response: "abc")
    service = ImageGenerationService.__new__(ImageGenerationService)
    import anyio
    result = anyio.run(service.generate_recipe_image, "Soup")
    assert result["success"] is True
    assert calls[0][0].endswith("lite-image")
    assert calls[1] == ("gemini-3.1-flash-image", "1K")
    assert sum(1 for model, _size in calls if model == calls[0][0]) == 1


def test_banner_route_is_gone_and_does_not_reserve_quota(file_db):
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(image_router, prefix="/api/ai/image-generation")

    def session_dependency():
        with file_db() as session:
            yield session

    with file_db() as session:
        user = session.get(User, 1)
    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    response = TestClient(app).post("/api/ai/image-generation/banner", json={"recipe_name": "Soup", "reference_image_data": "aa"})
    assert response.status_code == 410
    with file_db() as session:
        assert session.query(UserUsage).count() == 0


def test_rate_limit_429_does_not_reserve_quota(file_db):
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(image_router, prefix="/api/ai/image-generation")
    with file_db() as session:
        user = session.get(User, 1)
        user.subscription_tier = "pro"
        user.subscription_status = "active"
        session.commit()

    def session_dependency():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    with patch("app.api.auth.dependencies.enforce_pre_quota_limits", side_effect=RateLimitExceeded(MagicMock(limit="1/minute", error_message=None))):
        response = TestClient(app).post("/api/ai/image-generation", json={"recipe_name": "Soup", "image_type": "reference"})
    assert response.status_code == 429
    with file_db() as session:
        assert session.query(UserUsage).count() == 0


def test_pre_quota_limiter_rejects_the_second_hit():
    app = FastAPI()

    @app.get("/limited")
    def limited(request=Depends(lambda: None)):
        return {"ok": True}

    client = TestClient(app)
    # Build a request through the app so it is a real Request.
    seen = {}

    @app.get("/probe")
    def probe():
        return {"ok": True}

    with TestClient(app) as http:
        http.get("/probe")
    # Direct function check with a synthetic request.
    from starlette.requests import Request
    scope = {"type": "http", "method": "GET", "path": "/probe-limit", "headers": [], "query_string": b"", "client": ("203.0.113.5", 1234), "scheme": "http", "server": ("test", 80)}
    request = Request(scope)
    enforce_pre_quota_limits(request, ("1/minute",), ())
    with pytest.raises(RateLimitExceeded):
        enforce_pre_quota_limits(request, ("1/minute",), ())
    assert seen == {}


def test_legacy_free_users_stay_free_until_the_sunset_then_go_read_only(file_db, monkeypatch):
    from app.core import offer_windows
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    cutoff = datetime(2026, 6, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(offer_windows, "legacy_free_cutoff", lambda: cutoff)
    monkeypatch.setattr(offer_windows, "free_tier_sunset_at", lambda: future)
    with file_db() as session:
        user = session.get(User, 1)
        user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session.commit()
        assert user.usage_tier == "free"
        assert user.is_read_only is False
        assert user.is_legacy_free_account() is True
        assert apply_free_tier_sunset(session) == 0
    monkeypatch.setattr(offer_windows, "free_tier_sunset_at", lambda: past)
    monkeypatch.setattr(offer_windows, "sunset_is_due", lambda now=None: True)
    with file_db() as session:
        user = session.get(User, 1)
        user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        later = User(
            clerk_id="later",
            email="later@example.test",
            usage_plan="launch",
            is_admin=False,
            subscription_tier="free",
            subscription_status="active",
            has_used_trial=False,
            created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
        session.add(later)
        session.commit()
        assert apply_free_tier_sunset(session, now=datetime.now(timezone.utc)) == 1
        session.commit()
        assert user.read_only_at is not None
        assert user.is_read_only is True
        assert user.usage_tier == "expired"
        assert later.read_only_at is None
        assert later.is_legacy_free_account() is False


def test_unset_legacy_cutoff_grandfathers_nobody(monkeypatch):
    from app.core import offer_windows
    monkeypatch.delenv("LEGACY_FREE_CUTOFF", raising=False)
    monkeypatch.setattr(offer_windows, "legacy_free_cutoff", offer_windows.legacy_free_cutoff)
    user = _user(created_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    assert offer_windows.legacy_free_cutoff() is None
    assert user.is_legacy_free_account() is False


def test_household_hook_scales_pro_caps_and_can_meter_the_owner():
    from app.core import usage_limits as limits
    owner = _user(id=7, subscription_tier="pro", subscription_status="active")
    member = _user(id=8, subscription_tier="free", subscription_status="active")
    try:
        limits.set_household_usage_hooks(
            subject=lambda user: owner,
            multiplier=lambda user: limits.HOUSEHOLD_PRO_CAP_MULTIPLIER,
        )
        subject, images = limits.usage_meter(member, "ai_images_generated")
        assert subject.id == 7
        assert images == 30
        _, chats = limits.usage_meter(member, "ai_assistant_messages")
        assert chats == 450
        trial = _user(subscription_tier="pro", subscription_status="trialing")
        assert limits.get_user_monthly_limit(trial, "ai_images_generated") == 3
    finally:
        limits.set_household_usage_hooks(
            subject=limits.identity_usage_subject,
            multiplier=limits.no_household_multiplier,
        )


def test_sunset_reminder_is_due_30_days_out(monkeypatch):
    from app.core import offer_windows
    from app.services import free_tier_sunset as reminders
    sunset = datetime(2027, 3, 31, 23, 59, tzinfo=timezone.utc)
    monkeypatch.setattr(reminders, "free_tier_sunset_at", lambda: sunset)
    monkeypatch.setattr(
        offer_windows,
        "legacy_free_cutoff",
        lambda: datetime(2026, 12, 1, tzinfo=timezone.utc),
    )
    user = _user(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert reminders.due_reminder_kind(user, sunset - timedelta(days=30)) == "30"
    assert reminders.due_reminder_kind(user, sunset - timedelta(days=7)) == "7"
    assert reminders.due_reminder_kind(user, sunset - timedelta(days=1)) == "1"
    user.sunset_reminder_30_sent_at = sunset - timedelta(days=30)
    user.sunset_reminder_7_sent_at = sunset - timedelta(days=7)
    user.sunset_reminder_1_sent_at = sunset - timedelta(days=1)
    assert reminders.due_reminder_kind(user, sunset - timedelta(days=1)) is None


def test_read_only_blocks_creates_and_allows_reads(file_db):
    app = FastAPI()
    app.include_router(recipe_router, prefix="/api/recipes", dependencies=[Depends(reject_read_only_writes)])
    with file_db() as session:
        user = session.get(User, 1)
        user.read_only_at = datetime.now(timezone.utc)
        session.commit()

    def session_dependency():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    denied = client.post("/api/recipes", json={"recipe_name": "Soup"})
    assert denied.status_code == 403
    assert denied.json()["detail"]["error"] == "read_only"
    allowed = client.get("/api/recipes")
    assert allowed.status_code != 403


def test_thinking_level_minimal_is_supported_by_the_sdk():
    from google.genai import types
    config = types.ThinkingConfig(thinking_level="minimal")
    assert config.thinking_level.value == "MINIMAL"


def test_new_accounts_must_start_a_trial_for_ai(file_db, monkeypatch):
    from app.core import offer_windows
    from app.core.usage_limits import LEGACY_USAGE_LIMITS

    cutoff = datetime(2026, 6, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(offer_windows, "legacy_free_cutoff", lambda: cutoff)
    assert LEGACY_USAGE_LIMITS["pro"]["ai_images_generated"] == 150
    assert LEGACY_USAGE_LIMITS["pro"]["ai_assistant_messages"] == 500

    with file_db() as session:
        user = session.get(User, 1)
        user.is_admin = False
        user.subscription_tier = "free"
        user.subscription_status = "active"
        user.has_used_trial = False
        user.created_at = cutoff
        session.commit()
        assert user.is_legacy_free_account() is False
        assert user.usage_tier == "none"
        assert user.access_reason == "trial_required"
        assert get_user_monthly_limit(user, "ai_assistant_messages") == 0

        legacy = User(
            clerk_id="legacy-free",
            email="legacy@example.test",
            is_admin=False,
            usage_plan="legacy",
            subscription_tier="free",
            subscription_status="active",
            has_used_trial=False,
            created_at=cutoff - timedelta(seconds=1),
        )
        session.add(legacy)
        session.commit()
        assert legacy.usage_tier == "free"
        assert get_user_monthly_limit(legacy, "ai_images_generated") == 3

    from app.api.ai.assistant import router as assistant_router
    from app.api.ai.meal_suggestions import router as meal_router
    from app.api.ai.recipe_import import router as import_router

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(image_router, prefix="/api/ai/image-generation")
    app.include_router(assistant_router, prefix="/api/ai/assistant")
    app.include_router(meal_router, prefix="/api/ai/meal-suggestions")
    app.include_router(import_router, prefix="/api/ai/recipe-import")
    app.include_router(recipe_router, prefix="/api/recipes")

    def session_dependency():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    expected = {"error": "trial_required", "message": "Start your 7-day trial"}
    calls = [
        ("/api/ai/image-generation", {"recipe_name": "Soup", "image_type": "reference"}),
        ("/api/ai/assistant/chat", {"message": "What can I make?"}),
        ("/api/ai/meal-suggestions", {"main_recipe_name": "Soup"}),
        ("/api/ai/recipe-import", {"url": "https://example.test/soup"}),
    ]
    for path, body in calls:
        response = client.post(path, json=body)
        assert response.status_code == 403, path
        assert response.json()["detail"] == expected
    manual = client.post("/api/recipes", json={"recipe_name": "Soup", "recipe_category": "Dinner"})
    assert manual.status_code == 201
    with file_db() as session:
        assert session.query(UserUsage).count() == 0


def test_client_ip_uses_the_rightmost_forwarded_hop():
    from starlette.requests import Request
    from app.core.rate_limit import client_ip

    def request_for(forwarded: str | None, peer: str = "10.0.0.8") -> Request:
        headers = []
        if forwarded is not None:
            headers.append((b"x-forwarded-for", forwarded.encode()))
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "client": (peer, 1234),
            "scheme": "http",
            "server": ("test", 80),
        }
        return Request(scope)

    assert client_ip(request_for("1.2.3.4, 203.0.113.9")) == "203.0.113.9"
    assert client_ip(request_for(" 203.0.113.7 ")) == "203.0.113.7"
    assert client_ip(request_for(None, "10.0.0.8")) == "10.0.0.8"


def test_empty_or_safety_blocked_image_does_not_fall_back(monkeypatch, caplog):
    from app.services.ai.image_generation.service import ImageGenerationService
    from app.services.ai import image_generation as image_pkg

    calls = []

    async def generate_content(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1 and monkeypatch_mode["safety"]:
            return SimpleNamespace(prompt_feedback=SimpleNamespace(block_reason="SAFETY"), candidates=[])
        return SimpleNamespace(prompt_feedback=None, candidates=[])

    monkeypatch_mode = {"safety": False}
    client = MagicMock()
    client.aio.models.generate_content = generate_content
    monkeypatch.setattr(image_pkg.service, "get_gemini_client", lambda *a, **k: client)
    monkeypatch.setattr(image_pkg.service, "extract_image_data", lambda response: None)
    service = ImageGenerationService.__new__(ImageGenerationService)
    import anyio
    caplog.set_level("INFO")
    empty = anyio.run(service.generate_recipe_image, "Soup")
    assert empty["success"] is False
    assert len(calls) == 1
    assert "outcome=empty" in caplog.text

    calls.clear()
    caplog.clear()
    monkeypatch_mode["safety"] = True
    blocked = anyio.run(service.generate_recipe_image, "Soup")
    assert blocked["success"] is False
    assert len(calls) == 1
    assert "outcome=safety_blocked" in caplog.text
    assert "model=" in caplog.text


def test_only_one_checkout_receives_a_trial(file_db):
    import stripe
    from app.services.billing_service import CheckoutSessionError
    from app.services.stripe_webhook_service import StripeWebhookService

    with file_db() as session:
        user = session.get(User, 1)
        user.has_used_trial = False
        user.trial_started_at = None
        session.commit()
        service = BillingService(session, _settings())
        created = []

        def create(**kwargs):
            created.append(kwargs)
            return SimpleNamespace(id=f"cs_{len(created)}", url="https://pay.test/c")

        with patch("stripe.Customer.create", return_value=SimpleNamespace(id="cus_new")), \
             patch("stripe.Invoice.list", return_value=SimpleNamespace(data=[])), \
             patch("stripe.checkout.Session.create", side_effect=create):
            service.create_checkout_session(user, plan="monthly")
            service.create_checkout_session(user, plan="monthly")

        assert created[0]["subscription_data"]["trial_period_days"] == STRIPE_TRIAL_DAYS
        assert "trial_period_days" not in created[1].get("subscription_data", {})
        session.refresh(user)
        assert user.has_used_trial is True
        assert user.pending_trial_checkout_id == "cs_1"

        webhook = StripeWebhookService(session, _settings())
        webhook.handle_event({
            "id": "evt_expire",
            "type": "checkout.session.expired",
            "data": {"object": {"id": "cs_1", "customer": "cus_new", "mode": "subscription"}},
        })
        session.refresh(user)
        assert user.has_used_trial is False
        assert user.pending_trial_checkout_id is None

        user.has_used_trial = True
        user.pending_trial_checkout_id = "cs_used"
        user.trial_started_at = datetime.now(timezone.utc)
        session.commit()
        webhook.handle_event({
            "id": "evt_expire_used",
            "type": "checkout.session.expired",
            "data": {"object": {"id": "cs_used", "customer": "cus_new", "mode": "subscription"}},
        })
        session.refresh(user)
        assert user.has_used_trial is True

        user.has_used_trial = False
        user.pending_trial_checkout_id = None
        user.trial_started_at = None
        user.stripe_customer_id = None
        session.commit()
        with patch("stripe.Customer.create", return_value=SimpleNamespace(id="cus_fail")), \
             patch("stripe.checkout.Session.create", side_effect=stripe.error.APIConnectionError("down")):
            with pytest.raises(CheckoutSessionError):
                service.create_checkout_session(user, plan="monthly")
        session.refresh(user)
        assert user.has_used_trial is False
