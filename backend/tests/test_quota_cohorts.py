"""Existing-account entitlements survive the launch migration and upgrades."""
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from app.core.usage_limits import get_user_monthly_limit
from app.dtos.admin_dtos import AdminUsageLimitsDTO
from app.models.user import User


def test_existing_accounts_keep_legacy_caps_and_usage_display():
    user = User(is_admin=False, usage_plan="legacy", subscription_tier="pro", subscription_status="active")
    assert get_user_monthly_limit(user, "ai_images_generated") == 150
    assert AdminUsageLimitsDTO.for_user(user).ai_assistant_messages == 500
    user.subscription_tier = "free"
    assert get_user_monthly_limit(user, "ai_images_generated") == 3
    user.subscription_tier = "pro"
    assert get_user_monthly_limit(user, "ai_suggestions_requested") == 300


def test_new_account_gets_launch_caps():
    user = User(is_admin=False, usage_plan="launch", subscription_tier="pro", subscription_status="active")
    assert get_user_monthly_limit(user, "ai_images_generated") == 10
    assert AdminUsageLimitsDTO.for_user(user).ai_assistant_messages == 50


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
