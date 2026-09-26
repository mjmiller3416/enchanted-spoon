"""Tests for UserService.get_or_create_from_clerk account resolution."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from unittest.mock import MagicMock, patch

from app.models.user import User
from app.services import clerk_service
from app.services.user_service import AccountLinkError, UserService


def _verified(_clerk_id: str, _email: str) -> bool:
    return True


def _unverified(_clerk_id: str, _email: str) -> bool:
    return False


@pytest.fixture(autouse=True)
def no_starter_content(monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")


def _user_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(User))


class TestGetOrCreateFromClerk:
    def test_returning_user_matched_by_clerk_id(self, db_session, test_user):
        count = _user_count(db_session)
        user = UserService(db_session, email_verifier=_verified).get_or_create_from_clerk(
            test_user.clerk_id, test_user.email
        )

        assert user.id == test_user.id
        assert _user_count(db_session) == count

    def test_new_clerk_id_relinks_existing_email(self, db_session, test_user):
        """Moving Clerk instances issues new user IDs; the account must follow the email."""
        count = _user_count(db_session)
        user = UserService(db_session, email_verifier=_verified).get_or_create_from_clerk(
            "user_prod_instance", test_user.email, name="New Name"
        )

        assert user.id == test_user.id
        assert user.clerk_id == "user_prod_instance"
        assert user.name == "New Name"
        assert _user_count(db_session) == count

    def test_relinked_user_resolves_by_new_clerk_id(self, db_session, test_user):
        service = UserService(db_session, email_verifier=_verified)
        service.get_or_create_from_clerk("user_prod_instance", test_user.email)

        user = service.get_or_create_from_clerk("user_prod_instance", test_user.email)
        assert user.id == test_user.id

    def test_email_match_is_case_insensitive(self, db_session, test_user):
        user = UserService(db_session, email_verifier=_verified).get_or_create_from_clerk(
            "user_prod_instance", test_user.email.upper()
        )
        assert user.id == test_user.id

    def test_pending_claim_user_is_claimed(self, db_session):
        pending = User(clerk_id="pending_claim", email="maryann@example.com")
        db_session.add(pending)
        db_session.flush()

        user = UserService(db_session, email_verifier=_verified).get_or_create_from_clerk(
            "user_real", "maryann@example.com"
        )

        assert user.id == pending.id
        assert user.clerk_id == "user_real"

    def test_unknown_email_creates_new_user(self, db_session, test_user):
        count = _user_count(db_session)
        user = UserService(db_session, email_verifier=_verified).get_or_create_from_clerk(
            "user_brand_new", "brand-new@example.com"
        )

        assert user.id != test_user.id
        assert user.clerk_id == "user_brand_new"
        assert _user_count(db_session) == count + 1


class TestRelinkRequiresVerifiedEmail:
    def test_unverified_email_cannot_take_over_existing_account(self, db_session, test_user):
        original_clerk_id = test_user.clerk_id
        with pytest.raises(AccountLinkError):
            UserService(db_session, email_verifier=_unverified).get_or_create_from_clerk(
                "user_attacker", test_user.email
            )
        assert test_user.clerk_id == original_clerk_id

    def test_verifier_is_asked_about_the_signing_in_user(self, db_session, test_user):
        calls = []

        def verifier(clerk_id, email):
            calls.append((clerk_id, email))
            return True

        UserService(db_session, email_verifier=verifier).get_or_create_from_clerk(
            "user_prod_instance", test_user.email
        )
        assert calls == [("user_prod_instance", test_user.email)]

    def test_returning_user_email_is_kept_current(self, db_session, test_user):
        UserService(db_session, email_verifier=_unverified).get_or_create_from_clerk(
            test_user.clerk_id, "changed@example.com"
        )
        assert test_user.email == "changed@example.com"

    def test_email_sync_skips_address_held_by_another_account(self, db_session, test_user, second_user):
        UserService(db_session, email_verifier=_unverified).get_or_create_from_clerk(
            test_user.clerk_id, second_user.email
        )
        assert test_user.email == "test@example.com"


class TestClerkEmailVerification:
    def _clerk_user(self, status: str) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {
            "email_addresses": [
                {"email_address": "Owner@Example.com", "verification": {"status": status}}
            ]
        }
        return resp

    def test_verified_address_passes(self, monkeypatch):
        monkeypatch.setattr(clerk_service, "_secret_key", lambda: "sk_test")
        with patch.object(clerk_service.httpx, "get", return_value=self._clerk_user("verified")):
            assert clerk_service.clerk_user_has_verified_email("user_1", "owner@example.com")

    def test_unverified_address_fails(self, monkeypatch):
        monkeypatch.setattr(clerk_service, "_secret_key", lambda: "sk_test")
        with patch.object(clerk_service.httpx, "get", return_value=self._clerk_user("unverified")):
            assert not clerk_service.clerk_user_has_verified_email("user_1", "owner@example.com")

    def test_missing_secret_fails_closed(self, monkeypatch):
        monkeypatch.setattr(clerk_service, "_secret_key", lambda: None)
        assert not clerk_service.clerk_user_has_verified_email("user_1", "owner@example.com")

    def test_network_error_fails_closed(self, monkeypatch):
        monkeypatch.setattr(clerk_service, "_secret_key", lambda: "sk_test")
        with patch.object(
            clerk_service.httpx, "get", side_effect=clerk_service.httpx.ConnectError("down")
        ):
            assert not clerk_service.clerk_user_has_verified_email("user_1", "owner@example.com")


class TestConcurrentFirstSignIn:
    def test_losing_the_create_race_returns_the_winner(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database.base import Base

        engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine, expire_on_commit=False)()
        try:
            winner = User(clerk_id="user_race", email="race@example.com")
            session.add(winner)
            session.commit()

            service = UserService(session, email_verifier=_unverified)
            real_lookup = service.repo.get_by_clerk_id
            lookups = iter([None])  # first lookup misses, as if the winner hadn't committed yet

            def racing_lookup(clerk_id):
                return next(lookups, None) or real_lookup(clerk_id)

            with patch.object(service.repo, "get_by_clerk_id", side_effect=racing_lookup), patch.object(
                service.repo, "get_by_email", return_value=None
            ):
                user = service.get_or_create_from_clerk("user_race", "race@example.com")

            assert user.id == winner.id
        finally:
            session.close()
            engine.dispose()
