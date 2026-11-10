"""Existing-account entitlements survive the launch migration and upgrades."""
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from app.core.usage_limits import get_user_monthly_limit
from app.dtos.admin_dtos import AdminUsageLimitsDTO
from app.models.user import User


def test_legacy_pro_and_grants_use_launch_caps_unless_exempt(monkeypatch):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setenv("LEGACY_FREE_CUTOFF", "2026-06-01T00:00:00+00:00")
    monkeypatch.delenv("USAGE_EXEMPT_USER_IDS", raising=False)
    monkeypatch.delenv("ADMIN_EXEMPT_EMAILS", raising=False)
    user = User(
        id=4,
        is_admin=False,
        usage_plan="legacy",
        usage_exempt=False,
        subscription_tier="pro",
        subscription_status="active",
        has_used_trial=False,
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    assert get_user_monthly_limit(user, "ai_images_generated") == 20
    assert get_user_monthly_limit(user, "ai_assistant_messages") == 100
    assert get_user_monthly_limit(user, "ai_suggestions_requested") == 50
    assert get_user_monthly_limit(user, "recipes_imported") == 25
    assert AdminUsageLimitsDTO.for_user(user).ai_images_generated == 20
    user.subscription_tier = "free"
    assert user.usage_tier == "free"
    assert get_user_monthly_limit(user, "ai_images_generated") == 3
    user.subscription_tier = "pro"
    user.usage_exempt = True
    assert get_user_monthly_limit(user, "ai_images_generated") == 150
    assert get_user_monthly_limit(user, "ai_assistant_messages") == 500
    assert get_user_monthly_limit(user, "ai_suggestions_requested") == 300
    assert get_user_monthly_limit(user, "recipes_imported") == 100

    granted = User(
        id=9,
        is_admin=False,
        usage_plan="legacy",
        usage_exempt=False,
        subscription_tier="free",
        subscription_status="active",
        granted_pro_until=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    assert granted.usage_tier == "pro"
    assert get_user_monthly_limit(granted, "ai_images_generated") == 20
    monkeypatch.setenv("USAGE_EXEMPT_USER_IDS", "9, no, 42")
    assert get_user_monthly_limit(granted, "ai_images_generated") == 150
    user.usage_exempt = False
    assert get_user_monthly_limit(user, "ai_images_generated") == 20

    trialing = User(
        id=9,
        is_admin=False,
        usage_plan="legacy",
        usage_exempt=True,
        subscription_tier="pro",
        subscription_status="trialing",
    )
    assert get_user_monthly_limit(trialing, "ai_images_generated") == 3


def test_admin_exempt_emails_stay_admin_and_other_legacy_pro_uses_launch_caps(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException
    from app.api.auth.dependencies import require_admin
    from app.core.usage_limits import is_usage_exempt

    monkeypatch.delenv("USAGE_EXEMPT_USER_IDS", raising=False)
    monkeypatch.setenv(
        "ADMIN_EXEMPT_EMAILS",
        " Owner@Example.com , , partner@example.com ",
    )
    created = datetime(2020, 1, 1, tzinfo=timezone.utc)
    owner = User(
        id=1,
        email="owner@example.com",
        is_admin=True,
        usage_plan="legacy",
        usage_exempt=False,
        subscription_tier="pro",
        subscription_status="active",
        created_at=created,
    )
    partner = User(
        id=2,
        email="Partner@Example.com",
        is_admin=False,
        usage_plan="legacy",
        usage_exempt=False,
        subscription_tier="free",
        subscription_status="active",
        created_at=created,
    )
    other = User(
        id=3,
        email="subscriber@example.com",
        is_admin=False,
        usage_plan="legacy",
        usage_exempt=False,
        subscription_tier="pro",
        subscription_status="active",
        created_at=created,
    )
    granted = User(
        id=5,
        email="tester@example.com",
        is_admin=False,
        usage_plan="legacy",
        usage_exempt=False,
        subscription_tier="free",
        subscription_status="active",
        granted_pro_until=datetime.now(timezone.utc) + timedelta(days=14),
        created_at=created,
    )

    assert owner.keeps_admin_access() is True
    assert owner.access_reason == "admin"
    assert is_usage_exempt(owner) is False
    assert get_user_monthly_limit(owner, "ai_images_generated") is None
    # The database email is not a Clerk-verified primary, so it grants nothing.
    assert partner.keeps_admin_access() is False
    assert partner.has_pro_access is False
    assert is_usage_exempt(partner) is False
    assert get_user_monthly_limit(partner, "ai_assistant_messages") != None
    try:
        require_admin(partner)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("an unverified email claim was treated as admin")

    assert other.keeps_admin_access() is False
    assert get_user_monthly_limit(other, "ai_images_generated") == 20
    assert get_user_monthly_limit(other, "ai_assistant_messages") == 100
    assert get_user_monthly_limit(other, "ai_suggestions_requested") == 50
    assert get_user_monthly_limit(other, "recipes_imported") == 25
    assert granted.usage_tier == "pro"
    assert granted.keeps_admin_access() is False
    assert get_user_monthly_limit(granted, "ai_images_generated") == 20
    try:
        require_admin(other)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("legacy pro subscriber was treated as admin")


def test_new_account_gets_launch_caps():
    user = User(is_admin=False, usage_plan="launch", subscription_tier="pro", subscription_status="active")
    assert get_user_monthly_limit(user, "ai_images_generated") == 20
    assert AdminUsageLimitsDTO.for_user(user).ai_assistant_messages == 100


def test_migration_preserves_old_rows_and_new_orm_defaults(tmp_path, monkeypatch):
    from sqlalchemy.orm import Session
    backend = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{tmp_path / 'cohorts.db'}"
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", url)
    monkeypatch.chdir(backend)
    config = Config(str(backend / "alembic.ini"))
    command.upgrade(config, "e4a9c2d7b1f3")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (clerk_id,email,is_admin,subscription_tier,subscription_status,cancel_at_period_end,created_at,updated_at) VALUES ('old','old@example.test',0,'pro','active',0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT usage_plan FROM users WHERE clerk_id='old'")).scalar() == "legacy"
    with Session(engine) as session:
        user = User(clerk_id="new", email="new@example.test")
        session.add(user)
        session.commit()
        assert user.usage_plan == "launch"
    engine.dispose()
