"""ADMIN_EMAILS grants is_admin only for Clerk's verified primary email."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import clerk_service
from app.services.admin_grant import grant_admins_from_env
from app.services.user_service import UserService


@pytest.fixture(autouse=True)
def _clear_verified_email_cache():
    clerk_service.clear_verified_email_cache()
    yield
    clerk_service.clear_verified_email_cache()


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


def _clerk(
    *,
    primary: str,
    primary_status: str,
    secondary: str | None = None,
    secondary_status: str = "verified",
) -> dict:
    addresses = [
        {
            "id": "idn_primary",
            "email_address": primary,
            "verification": {"status": primary_status},
        }
    ]
    if secondary is not None:
        addresses.append(
            {
                "id": "idn_secondary",
                "email_address": secondary,
                "verification": {"status": secondary_status},
            }
        )
    return {"primary_email_address_id": "idn_primary", "email_addresses": addresses}


def _patch_clerk(monkeypatch, payloads: dict[str, dict | None]) -> list[str]:
    calls: list[str] = []

    def fetch(clerk_id: str):
        calls.append(clerk_id)
        return payloads.get(clerk_id)

    monkeypatch.setattr(clerk_service, "fetch_clerk_user", fetch)
    return calls


def _verified(email: str) -> dict:
    return _clerk(primary=email, primary_status="verified")


@pytest.mark.parametrize("raw", [None, "", "   ", ",", " , , "])
def test_unset_or_blank_admin_emails_does_nothing(db_session, monkeypatch, raw):
    if raw is None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    else:
        monkeypatch.setenv("ADMIN_EMAILS", raw)
    calls = _patch_clerk(monkeypatch, {"regular": _verified("person@example.com")})
    admin = _user(db_session, clerk_id="admin-keep", email="keep@example.com", is_admin=True)
    regular = _user(db_session, clerk_id="regular", email="person@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0

    assert calls == []
    assert not db_session.dirty
    assert admin.is_admin is True
    assert regular.is_admin is False


def test_verified_primary_grants_and_unlisted_users_stay_put(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com, other@example.com")
    _patch_clerk(
        monkeypatch,
        {
            "listed": _verified("admin@example.com"),
            "also": _verified("other@example.com"),
            "stranger": _verified("nope@example.com"),
            "already": _clerk(primary="boss@example.com", primary_status="unverified"),
        },
    )
    listed = _user(db_session, clerk_id="listed", email="admin@example.com", is_admin=False)
    also_listed = _user(db_session, clerk_id="also", email="other@example.com", is_admin=False)
    stranger = _user(db_session, clerk_id="stranger", email="nope@example.com", is_admin=False)
    already = _user(db_session, clerk_id="already", email="boss@example.com", is_admin=True)

    assert grant_admins_from_env(db_session) == 2

    assert listed.is_admin is True
    assert also_listed.is_admin is True
    assert stranger.is_admin is False
    assert already.is_admin is True


def test_verified_primary_grants_when_stored_email_is_stale(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    _patch_clerk(monkeypatch, {"stale": _verified("Admin@Example.com")})
    user = _user(db_session, clerk_id="stale", email="old@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 1

    assert user.is_admin is True
    assert user.email == "old@example.com"


def test_listed_stored_email_with_unverified_primary_does_not_grant(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    _patch_clerk(
        monkeypatch,
        {"unverified": _clerk(primary="admin@example.com", primary_status="unverified")},
    )
    user = _user(db_session, clerk_id="unverified", email="admin@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0
    assert user.is_admin is False


def test_verified_secondary_does_not_grant(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    _patch_clerk(
        monkeypatch,
        {
            "secondary": _clerk(
                primary="other@example.com",
                primary_status="verified",
                secondary="admin@example.com",
                secondary_status="verified",
            )
        },
    )
    user = _user(db_session, clerk_id="secondary", email="admin@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0
    assert user.is_admin is False


def test_clerk_miss_does_not_grant(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    _patch_clerk(monkeypatch, {"missing": None})
    user = _user(db_session, clerk_id="missing", email="admin@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0
    assert user.is_admin is False


def test_unconfigured_clerk_does_not_grant_or_call_http(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setattr(clerk_service, "_secret_key", lambda: None)

    def fail_http(*_args, **_kwargs):
        raise AssertionError("unconfigured Clerk must not make an HTTP call")

    monkeypatch.setattr(clerk_service.httpx, "get", fail_http)
    user = _user(db_session, clerk_id="user_real", email="admin@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0
    assert user.is_admin is False


def test_pending_claim_and_blank_clerk_id_do_not_grant_or_call_clerk(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    calls = _patch_clerk(
        monkeypatch,
        {
            "pending_claim": _verified("admin@example.com"),
            "": _verified("admin@example.com"),
        },
    )
    pending = _user(db_session, clerk_id="pending_claim", email="admin@example.com", is_admin=False)
    blank = _user(db_session, clerk_id="  ", email="blank@example.com", is_admin=False)

    assert grant_admins_from_env(db_session) == 0
    assert calls == []
    assert pending.is_admin is False
    assert blank.is_admin is False


def test_already_admin_stays_admin_and_rerun_is_a_noop(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    calls = _patch_clerk(
        monkeypatch,
        {
            "listed-admin": _clerk(primary="admin@example.com", primary_status="unverified"),
            "outsider-admin": _verified("someone-else@example.com"),
        },
    )
    listed = _user(db_session, clerk_id="listed-admin", email="admin@example.com", is_admin=True)
    outsider = _user(db_session, clerk_id="outsider-admin", email="boss@example.com", is_admin=True)

    assert grant_admins_from_env(db_session) == 0
    assert calls == []
    assert listed.is_admin is True
    assert outsider.is_admin is True

    listed.is_admin = False
    db_session.flush()
    calls.clear()
    _patch_clerk(monkeypatch, {"listed-admin": _verified("admin@example.com")})
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
    _patch_clerk(
        monkeypatch,
        {
            "mixed": _verified("admin@example.com"),
            "upper": _clerk(primary="  SECOND@example.com ", primary_status="verified"),
            "padded": _verified("second-pad@example.com"),
        },
    )
    mixed = _user(db_session, clerk_id="mixed", email="other@example.com", is_admin=False)
    upper = _user(db_session, clerk_id="upper", email="nope@example.com", is_admin=False)
    padded = _user(db_session, clerk_id="padded", email="  second-pad@example.com ", is_admin=False)

    assert grant_admins_from_env(db_session) == 3
    assert mixed.is_admin is True
    assert upper.is_admin is True
    assert padded.is_admin is True
    assert grant_admins_from_env(db_session) == 0


def test_sign_in_grants_verified_primary_and_repeat_sign_in_is_a_noop(db_session, monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
    monkeypatch.setenv("ADMIN_EMAILS", "  New@Example.com ")
    _patch_clerk(monkeypatch, {"clerk_new": _verified("new@example.com")})
    service = UserService(db_session, email_verifier=lambda *_args: True)

    user = service.get_or_create_from_clerk("clerk_new", "stale@example.com")
    assert user.email == "stale@example.com"
    assert user.is_admin is True

    again = service.get_or_create_from_clerk("clerk_new", "stale@example.com")
    assert again.id == user.id
    assert again.is_admin is True


def test_sign_in_does_not_grant_from_unverified_or_secondary_email(db_session, monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    _patch_clerk(
        monkeypatch,
        {
            "clerk_unverified": _clerk(primary="admin@example.com", primary_status="unverified"),
            "clerk_secondary": _clerk(
                primary="other@example.com",
                primary_status="verified",
                secondary="admin@example.com",
                secondary_status="verified",
            ),
        },
    )
    service = UserService(db_session, email_verifier=lambda *_args: True)

    unverified = service.get_or_create_from_clerk("clerk_unverified", "admin@example.com")
    secondary = service.get_or_create_from_clerk("clerk_secondary", "admin@example.com")

    assert unverified.email == "admin@example.com"
    assert unverified.is_admin is False
    assert secondary.email == "admin@example.com"
    assert secondary.is_admin is False


def test_sign_in_leaves_unlisted_and_existing_admins_alone(db_session, monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    calls = _patch_clerk(monkeypatch, {})
    service = UserService(db_session, email_verifier=lambda *_args: True)
    created = service.get_or_create_from_clerk("clerk_plain", "plain@example.com")
    assert created.is_admin is False
    assert calls == []

    monkeypatch.setenv("ADMIN_EMAILS", "someone@example.com")
    _patch_clerk(
        monkeypatch,
        {
            "clerk_boss": _clerk(primary="boss@example.com", primary_status="unverified"),
            "clerk_plain": _verified("plain@example.com"),
        },
    )
    boss = _user(db_session, clerk_id="clerk_boss", email="boss@example.com", is_admin=True)
    signed_in = service.get_or_create_from_clerk("clerk_boss", "boss@example.com")
    plain = service.get_or_create_from_clerk("clerk_plain", "plain@example.com")

    assert signed_in.id == boss.id
    assert signed_in.is_admin is True
    assert plain.is_admin is False


def test_sign_in_pending_claim_does_not_grant(db_session, monkeypatch):
    monkeypatch.setenv("SEED_STARTER_CONTENT", "false")
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    calls = _patch_clerk(monkeypatch, {"pending_claim": _verified("admin@example.com")})
    service = UserService(db_session, email_verifier=lambda *_args: True)

    user = service.get_or_create_from_clerk("pending_claim", "admin@example.com")

    assert calls == []
    assert user.is_admin is False


def test_startup_helper_grants_verified_primary_and_is_idempotent(file_db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " Admin@Example.com ")
    _patch_clerk(
        monkeypatch,
        {
            "startup-admin": _verified("admin@example.com"),
            "startup-keep": _clerk(primary="keep@example.com", primary_status="unverified"),
            "file_db_user_1": _verified("u1@example.com"),
        },
    )
    with file_db() as session:
        session.add(User(clerk_id="startup-admin", email="old@example.com", is_admin=False))
        session.add(User(clerk_id="startup-keep", email="admin@example.com", is_admin=True))
        session.commit()
    monkeypatch.setattr("app.main.SessionLocal", file_db)

    from app.main import _grant_admins_from_env

    _grant_admins_from_env()
    _grant_admins_from_env()

    with file_db() as session:
        granted = session.scalars(select(User).where(User.clerk_id == "startup-admin")).one()
        kept = session.scalars(select(User).where(User.clerk_id == "startup-keep")).one()
        seeded = session.scalars(select(User).where(User.clerk_id == "file_db_user_1")).one()
        assert granted.is_admin is True
        assert granted.email == "old@example.com"
        assert kept.is_admin is True
        assert seeded.is_admin is False


def test_startup_helper_does_not_grant_without_a_verified_primary(file_db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    _patch_clerk(
        monkeypatch,
        {
            "startup-unverified": _clerk(primary="admin@example.com", primary_status="unverified"),
            "startup-secondary": _clerk(
                primary="other@example.com",
                primary_status="verified",
                secondary="admin@example.com",
                secondary_status="verified",
            ),
            "startup-miss": None,
            "file_db_user_1": None,
        },
    )
    with file_db() as session:
        session.add(User(clerk_id="startup-unverified", email="admin@example.com", is_admin=False))
        session.add(User(clerk_id="startup-secondary", email="secondary@example.com", is_admin=False))
        session.add(User(clerk_id="startup-miss", email="miss@example.com", is_admin=False))
        session.add(User(clerk_id="pending_claim", email="pending@example.com", is_admin=False))
        session.commit()
    monkeypatch.setattr("app.main.SessionLocal", file_db)

    from app.main import _grant_admins_from_env

    _grant_admins_from_env()

    with file_db() as session:
        rows = {
            user.clerk_id: user
            for user in session.scalars(select(User)).all()
        }
        assert rows["startup-unverified"].is_admin is False
        assert rows["startup-secondary"].is_admin is False
        assert rows["startup-miss"].is_admin is False
        assert rows["pending_claim"].is_admin is False


def test_startup_helper_skips_the_database_and_clerk_when_unset(file_db, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    calls = _patch_clerk(monkeypatch, {"file_db_user_1": _verified("u1@example.com")})
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
    assert calls == []
