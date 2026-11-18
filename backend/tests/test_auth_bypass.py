"""AUTH_DISABLED is a local switch, including when startup validation did not run.

Startup already refuses to boot production with the bypass on. These tests
cover the request path that remains if that guard is skipped or changed:
production falls through to JWT checks, and local development still returns
the dev user.
"""

import logging

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import get_current_user_optional
from app.api.auth import dependencies as auth_dependencies
from app.api.users import router as users_router
from app.core.auth_config import get_auth_settings
from app.core.startup import ConfigError, validate_config
from app.database.db import get_session
from app.models.user import User

_PRODUCTION_ENV_VARS = (
    "ENVIRONMENT",
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_ENVIRONMENT_NAME",
)
_BYPASS_LOG = (
    "AUTH_DISABLED is set in a production environment; "
    "ignoring the development authentication bypass and requiring a JWT."
)


@pytest.fixture
def configured_auth(monkeypatch):
    """Patch env and the cached AuthSettings object, then drop the cache after."""

    def apply(
        *,
        auth_disabled: bool,
        environment: str | None = None,
        railway_name: str | None = None,
    ):
        for name in (*_PRODUCTION_ENV_VARS, "AUTH_DISABLED"):
            monkeypatch.delenv(name, raising=False)
        if environment is not None:
            monkeypatch.setenv("ENVIRONMENT", environment)
        if railway_name is not None:
            monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", railway_name)
        monkeypatch.setenv("AUTH_DISABLED", "true" if auth_disabled else "false")
        get_auth_settings.cache_clear()
        settings = get_auth_settings()
        monkeypatch.setattr(settings, "auth_disabled", auth_disabled)
        auth_dependencies._production_auth_bypass_logged = False
        return settings

    yield apply

    get_auth_settings.cache_clear()
    auth_dependencies._production_auth_bypass_logged = False


def _client(file_db) -> TestClient:
    """Protected and optional routes on the real auth dependencies.

    No app lifespan, so ``validate_config`` does not run. That is the case
    the request-time guard exists for.
    """
    app = FastAPI()
    app.include_router(users_router, prefix="/api/users")

    def _session():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = _session

    @app.get("/optional")
    def optional(user: User | None = Depends(get_current_user_optional)):
        if user is None:
            return {"id": None, "email": None}
        return {"id": user.id, "email": user.email}

    return TestClient(app)


class TestValidateConfigAuthDisabled:
    @pytest.mark.parametrize(
        ("environment", "railway_name"),
        [
            ("production", None),
            (None, "production"),
        ],
    )
    def test_refuses_auth_disabled_in_production(
        self, configured_auth, environment, railway_name
    ):
        settings = configured_auth(
            auth_disabled=True,
            environment=environment,
            railway_name=railway_name,
        )
        assert settings.auth_disabled is True
        with pytest.raises(ConfigError, match="AUTH_DISABLED"):
            validate_config()

    @pytest.mark.parametrize(
        ("environment", "railway_name"),
        [
            (None, None),
            ("development", None),
            (None, "staging"),
        ],
    )
    def test_allows_auth_disabled_outside_production(
        self, configured_auth, environment, railway_name
    ):
        configured_auth(
            auth_disabled=True,
            environment=environment,
            railway_name=railway_name,
        )
        validate_config()


class TestRequestTimeAuthBypass:
    @pytest.mark.parametrize(
        ("environment", "railway_name"),
        [
            ("production", None),
            (None, "production"),
        ],
    )
    def test_production_does_not_return_the_dev_user(
        self, configured_auth, file_db, caplog, environment, railway_name
    ):
        settings = configured_auth(
            auth_disabled=True,
            environment=environment,
            railway_name=railway_name,
        )
        assert settings.auth_disabled is True
        client = _client(file_db)
        caplog.set_level(logging.ERROR, logger="app.api.auth.dependencies")
        caplog.clear()

        protected = client.get("/api/users/me")
        assert protected.status_code == 401
        assert protected.json()["detail"] == "Missing authentication token"
        assert protected.headers["www-authenticate"] == "Bearer"
        assert "u1@example.com" not in protected.text

        optional = client.get("/optional")
        assert optional.status_code == 200
        assert optional.json() == {"id": None, "email": None}

        assert client.get("/api/users/me").status_code == 401
        refusals = [record for record in caplog.records if record.levelno >= logging.ERROR]
        assert [record.getMessage() for record in refusals] == [_BYPASS_LOG]

    @pytest.mark.parametrize(
        ("environment", "railway_name"),
        [
            (None, None),
            ("development", None),
            (None, "staging"),
        ],
    )
    def test_dev_bypass_still_works_outside_production(
        self, configured_auth, file_db, caplog, environment, railway_name
    ):
        configured_auth(
            auth_disabled=True,
            environment=environment,
            railway_name=railway_name,
        )
        client = _client(file_db)
        caplog.set_level(logging.ERROR, logger="app.api.auth.dependencies")
        caplog.clear()

        protected = client.get("/api/users/me")
        assert protected.status_code == 200
        assert protected.json()["id"] == 1
        assert protected.json()["email"] == "u1@example.com"

        optional = client.get("/optional")
        assert optional.status_code == 200
        assert optional.json() == {"id": 1, "email": "u1@example.com"}
        assert _BYPASS_LOG not in caplog.text
