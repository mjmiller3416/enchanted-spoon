"""app/repositories/oauth_repo.py

Data access for the OAuth authorization server (clients, codes, tokens).
Flushes only; OAuthService owns the transaction and commits.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models.oauth import OAuthAuthorizationCode, OAuthClient, OAuthToken


class OAuthRepo:
    """Reads and writes OAuth rows. Every lookup is by a SHA-256 digest or public id."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Clients ─────────────────────────────────────────────────────────────
    def add_client(self, client: OAuthClient) -> OAuthClient:
        """Stage a new client and flush so it has an id."""
        self.session.add(client)
        self.session.flush()
        return client

    def get_client(self, client_id: str) -> Optional[OAuthClient]:
        """The client with this public client_id, or None."""
        return self.session.scalar(select(OAuthClient).where(OAuthClient.client_id == client_id))

    def get_clients(self, client_ids: List[str]) -> List[OAuthClient]:
        """Clients for a set of client_ids (unknown ids are skipped)."""
        if not client_ids:
            return []
        return list(self.session.scalars(select(OAuthClient).where(OAuthClient.client_id.in_(client_ids))))

    def delete_client(self, client: OAuthClient) -> None:
        """Remove a client registration."""
        self.session.delete(client)
        self.session.flush()

    # ── Authorization codes ─────────────────────────────────────────────────
    def add_code(self, code: OAuthAuthorizationCode) -> OAuthAuthorizationCode:
        """Stage a new authorization code."""
        self.session.add(code)
        self.session.flush()
        return code

    def get_code(self, code_hash: str, *, for_update: bool = False) -> Optional[OAuthAuthorizationCode]:
        """The code with this digest, locked for update when asked (Postgres; a no-op on SQLite)."""
        stmt = select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code_hash == code_hash)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def mark_code_used(self, code_id: int, now: datetime) -> bool:
        """Mark a code used, only if it isn't already; True when this call won the race."""
        result = self.session.execute(
            update(OAuthAuthorizationCode)
            .where(OAuthAuthorizationCode.id == code_id, OAuthAuthorizationCode.used_at.is_(None))
            .values(used_at=now)
        )
        self.session.flush()
        return result.rowcount == 1

    # ── Tokens ──────────────────────────────────────────────────────────────
    def add_token(self, token: OAuthToken) -> OAuthToken:
        """Stage a new access or refresh token."""
        self.session.add(token)
        self.session.flush()
        return token

    def get_token(self, token_hash: str, *, for_update: bool = False) -> Optional[OAuthToken]:
        """The token with this digest, or None."""
        stmt = select(OAuthToken).where(OAuthToken.token_hash == token_hash)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def revoke_token(self, token_id: int, now: datetime) -> bool:
        """Revoke one token if it is still live; True when this call revoked it."""
        result = self.session.execute(
            update(OAuthToken)
            .where(OAuthToken.id == token_id, OAuthToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        self.session.flush()
        return result.rowcount == 1

    def revoke_grant(self, grant_id: str, now: datetime) -> int:
        """Revoke every live token of a grant; returns how many."""
        result = self.session.execute(
            update(OAuthToken)
            .where(OAuthToken.grant_id == grant_id, OAuthToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        self.session.flush()
        return result.rowcount or 0

    def revoke_user_tokens(self, user_id: int, now: datetime) -> int:
        """Revoke every live token a user has granted; returns how many."""
        result = self.session.execute(
            update(OAuthToken)
            .where(OAuthToken.user_id == user_id, OAuthToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        self.session.flush()
        return result.rowcount or 0

    def live_refresh_tokens(self, user_id: int, now: datetime) -> List[OAuthToken]:
        """A user's unrevoked, unexpired refresh tokens (one per live connection)."""
        return list(
            self.session.scalars(
                select(OAuthToken)
                .where(
                    OAuthToken.user_id == user_id,
                    OAuthToken.kind == "refresh",
                    OAuthToken.revoked_at.is_(None),
                    OAuthToken.expires_at > now,
                )
                .order_by(OAuthToken.created_at.desc())
            )
        )
