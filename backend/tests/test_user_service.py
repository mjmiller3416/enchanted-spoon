"""Tests for UserService.get_or_create_from_clerk account resolution."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service import UserService


@pytest.fixture(autouse=True)
def no_starter_content(monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")


def _user_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(User))


class TestGetOrCreateFromClerk:
    def test_returning_user_matched_by_clerk_id(self, db_session, test_user):
        count = _user_count(db_session)
        user = UserService(db_session).get_or_create_from_clerk(
            test_user.clerk_id, test_user.email
        )

        assert user.id == test_user.id
        assert _user_count(db_session) == count

    def test_new_clerk_id_relinks_existing_email(self, db_session, test_user):
        """Moving Clerk instances issues new user IDs; the account must follow the email."""
        count = _user_count(db_session)
        user = UserService(db_session).get_or_create_from_clerk(
            "user_prod_instance", test_user.email, name="New Name"
        )

        assert user.id == test_user.id
        assert user.clerk_id == "user_prod_instance"
        assert user.name == "New Name"
        assert _user_count(db_session) == count

    def test_relinked_user_resolves_by_new_clerk_id(self, db_session, test_user):
        service = UserService(db_session)
        service.get_or_create_from_clerk("user_prod_instance", test_user.email)

        user = service.get_or_create_from_clerk("user_prod_instance", test_user.email)
        assert user.id == test_user.id

    def test_email_match_is_case_insensitive(self, db_session, test_user):
        user = UserService(db_session).get_or_create_from_clerk(
            "user_prod_instance", test_user.email.upper()
        )
        assert user.id == test_user.id

    def test_pending_claim_user_is_claimed(self, db_session):
        pending = User(clerk_id="pending_claim", email="maryann@example.com")
        db_session.add(pending)
        db_session.flush()

        user = UserService(db_session).get_or_create_from_clerk(
            "user_real", "maryann@example.com"
        )

        assert user.id == pending.id
        assert user.clerk_id == "user_real"

    def test_unknown_email_creates_new_user(self, db_session, test_user):
        count = _user_count(db_session)
        user = UserService(db_session).get_or_create_from_clerk(
            "user_brand_new", "brand-new@example.com"
        )

        assert user.id != test_user.id
        assert user.clerk_id == "user_brand_new"
        assert _user_count(db_session) == count + 1
