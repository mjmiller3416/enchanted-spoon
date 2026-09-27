"""Production detection for the startup config guard."""

import pytest

from app.core.startup import is_production


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)


def test_defaults_to_development():
    assert is_production() is False


def test_explicit_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "Production")
    assert is_production() is True


def test_railway_production_counts_without_environment(monkeypatch):
    """Railway injects this on every deploy; the guard must not depend on a manual variable."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    assert is_production() is True


def test_railway_staging_is_not_production(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")
    assert is_production() is False


def test_explicit_environment_wins(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert is_production() is False
