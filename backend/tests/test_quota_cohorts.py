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
    assert get_user_monthly_limit(user, "ai_assistant_messages") == 300
    assert get_user_monthly_limit(user, "ai_suggestions_requested") == 200
    assert get_user_monthly_limit(user, "recipes_imported") == 50
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


def test_new_account_gets_launch_caps():
    user = User(is_admin=False, usage_plan="launch", subscription_tier="pro", subscription_status="active")
    assert get_user_monthly_limit(user, "ai_images_generated") == 20
    assert AdminUsageLimitsDTO.for_user(user).ai_assistant_messages == 300


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
