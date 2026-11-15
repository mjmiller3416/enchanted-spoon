"""app/models/oauth.py

ORM models for the OAuth 2.1 authorization server that ChatGPT custom
connectors use to reach the MCP server (``/api/mcp``).

Secrets are never stored: client secrets, authorization codes and tokens are
kept only as SHA-256 hex digests. A *grant* is one consent (one authorization
code); the access and refresh tokens it leads to share its ``grant_id``, so a
reused code or a revoked refresh token can take the whole grant down.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class OAuthClient(Base):
    """A client registered through dynamic client registration (RFC 7591)."""

    __tablename__ = "oauth_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    client_secret_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # JSON-encoded lists
    redirect_uris: Mapped[str] = mapped_column(Text, nullable=False)
    grant_types: Mapped[str] = mapped_column(Text, nullable=False)
    token_endpoint_auth_method: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<OAuthClient(client_id='{self.client_id}', name='{self.client_name}')>"


class OAuthAuthorizationCode(Base):
    """A single-use authorization code, bound to its client, redirect URI, PKCE challenge and user."""

    __tablename__ = "oauth_authorization_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    grant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<OAuthAuthorizationCode(client_id='{self.client_id}', user_id={self.user_id})>"


class OAuthToken(Base):
    """An access or refresh token (``kind``), stored as its SHA-256 digest."""

    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "access" | "refresh"
    grant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<OAuthToken(kind='{self.kind}', client_id='{self.client_id}', user_id={self.user_id})>"
