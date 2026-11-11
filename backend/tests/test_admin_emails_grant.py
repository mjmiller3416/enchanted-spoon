"""ADMIN_EMAILS grants is_admin and never removes it."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.admin_grant import grant_admins_from_env
from app.services.user_service import UserService


def _user(session: Session, *, clerk_id: str, email: str, is_admin: bool) -> User:
    user = User(
        clerk_id=clerk_id,
        email=email,
        is_admin=is_admin,
        subscription_tier="free",
    )
    session.add(user)
    session.flush()
    return user


@pytest.mark.parametrize("raw", [None, "", "   ", ",", " , , "])
def test_unset_or_blank_admin_emails_does_nothing(db_session, monkeypatch, raw):
    if raw is None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    else:
        monkeypatch.setenv("ADMIN_EMAILS", raw)
    admin = _user(db_session, clerk_id="admin-keep", email="keep@example.com", is_admin=True)
    regular = _user(db_session, clerk_id="regular", email="person@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0

    assert not db_session.dirty
    assert admin.is_admin is True
    assert regular.is_admin is False


def test_listed_emails_become_admin_and_others_stay_put(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com, other@example.com")
    listed = _user(db_session, clerk_id="listed", email="admin@example.com", is_admin=False)
    also_listed = _user(db_session, clerk_id="also", email="other@example.com", is_admin=False)
    stranger = _user(db_session, clerk_id="stranger", email="nope@example.com", is_admin=False)
    already = _user(db_session, clerk_id="already", email="boss@example.com", is_admin=True)

    assert grant_admins_from_env(db_session) == 2

    assert listed.is_admin is True
    assert also_listed.is_admin is True
    assert stranger.is_admin is False
    assert already.is_admin is True


def test_already_admin_stays_admin_and_rerun_is_a_noop(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    listed = _user(db_session, clerk_id="listed-admin", email="admin@example.com", is_admin=True)
    outsider = _user(db_session, clerk_id="outsider-admin", email="boss@example.com", is_admin=True)

    assert grant_admins_from_env(db_session) == 0
    assert listed.is_admin is True
    assert outsider.is_admin is True

    listed.is_admin = False
    db_session.flush()
    assert grant_admins_from_env(db_session) == 1
    assert listed.is_admin is True
    assert outsider.is_admin is True
    assert grant_admins_from_env(db_session) == 0
    assert listed.is_admin is True
    assert outsider.is_admin is True


def test_whitespace_and_case_are_ignored(db_session, monkeypatch):
    monkeypatch.setenv(
        "ADMIN_EMAILS",
        "  Admin@Example.com , SECOND@example.com ,  second-pad@example.com ",
    )
    mixed = _user(db_session, clerk_id="mixed", email="admin@example.com", is_admin=False)
    upper = _user(db_session, clerk_id="upper", email="second@example.com", is_admin=False)
    padded = _user(db_session, clerk_id="padded", email="  second-pad@example.com ", is_admin=False)

    assert grant_admins_from_env(db_session) == 3
    assert mixed.is_admin is True
    assert upper.is_admin is True
    assert padded.is_admin is True
    assert grant_admins_from_env(db_session) == 0


def test_sign_in_grants_listed_email_and_repeat_sign_in_is_a_noop(db_session, monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
    monkeypatch.setenv("ADMIN_EMAILS", "  New@Example.com ")
    service = UserService(db_session, email_verifier=lambda *_args: True)

    user = service.get_or_create_from_clerk("clerk_new", "new@example.com")
    assert user.is_admin is True

    again = service.get_or_create_from_clerk("clerk_new", "new@example.com")
    assert again.id == user.id
    assert again.is_admin is True


def test_sign_in_leaves_unlisted_and_existing_admins_alone(db_session, monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    service = UserService(db_session, email_verifier=lambda *_args: True)
    created = service.get_or_create_from_clerk("clerk_plain", "plain@example.com")
    assert created.is_admin is False

    monkeypatch.setenv("ADMIN_EMAILS", "someone@example.com")
    boss = _user(db_session, clerk_id="clerk_boss", email="boss@example.com", is_admin=True)
    signed_in = service.get_or_create_from_clerk("clerk_boss", "boss@example.com")
    plain = service.get_or_create_from_clerk("clerk_plain", "plain@example.com")

    assert signed_in.id == boss.id
    assert signed_in.is_admin is True
    assert plain.is_admin is False


def test_startup_helper_grants_and_is_idempotent(file_db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " Admin@Example.com ")
    with file_db() as session:
        session.add(User(clerk_id="startup-admin", email="admin@example.com", is_admin=False))
        session.add(User(clerk_id="startup-keep", email="keep@example.com", is_admin=True))
        session.commit()
    monkeypatch.setattr("app.main.SessionLocal", file_db)

    from app.main import _grant_admins_from_env

    _grant_admins_from_env()
    _grant_admins_from_env()

    with file_db() as session:
        granted = session.scalars(select(User).where(User.clerk_id == "startup-admin")).one()
        kept = session.scalars(select(User).where(User.clerk_id == "startup-keep")).one()
        assert granted.is_admin is True
        assert kept.is_admin is True


def test_startup_helper_skips_the_database_when_unset(file_db, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    opened = {"count": 0}

    def fail_if_opened():
        opened["count"] += 1
        raise AssertionError("ADMIN_EMAILS is unset; startup must not open a session")

    monkeypatch.setattr("app.main.SessionLocal", fail_if_opened)
    with file_db() as session:
        user = session.scalars(select(User).where(User.id == 1)).one()
        user.is_admin = False
        session.commit()

    from app.main import _grant_admins_from_env

    _grant_admins_from_env()
    assert opened["count"] == 0
