"""app/services/alexa/link_service.py

Voice pairing: links an Alexa account to Enchanted Spoon without the Alexa
app's account-linking card (which the current Alexa app may never show).

1. An unlinked Alexa account opens the skill. Alexa reads out a six-digit
   code (10 minutes, one use), bound to that Alexa ``userId``.
2. The person enters it in Enchanted Spoon (Settings → Connected Apps →
   Connect Alexa) while signed in. From then on the skill acts as them.

The ``userId`` only ever arrives inside Amazon-signed requests (checked in
``verification.py``), so nothing else can claim a link. Both it and the code
are stored as SHA-256 digests. Disconnecting in Settings deletes the link;
deleting the account cascades.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from ...models.alexa_link import AlexaLink
from ...repositories.alexa_link_repo import AlexaLinkRepo

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
CODE_DIGITS = 6


class AlexaPairingError(Exception):
    """A pairing code that doesn't match a waiting Alexa account (wrong, used or expired)."""


@dataclass(frozen=True)
class AlexaConnection:
    """One linked Alexa account, for Settings."""

    connected_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    """SQLite hands datetimes back naive; they were stored as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_code(raw: str) -> str:
    """Digits only, so "482 915" and "482-915" both work."""
    return "".join(ch for ch in raw if ch.isdigit())


class AlexaLinkService:
    """Issues and redeems pairing codes; commits its own changes."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AlexaLinkRepo(session)

    def user_for_alexa_user(self, alexa_user_id: str) -> Optional[int]:
        """The Enchanted Spoon account an Alexa account is linked to, if any."""
        row = self.repo.get_by_alexa_user(_digest(alexa_user_id))
        return row.user_id if row is not None and row.user_id is not None else None

    def issue_code(self, alexa_user_id: str) -> str:
        """A fresh code for an unlinked Alexa account (replacing any earlier one)."""
        now = _now()
        for _ in range(5):
            code = "".join(secrets.choice("0123456789") for _ in range(CODE_DIGITS))
            if self.repo.find_live_code(_digest(code), now) is None:
                break
        alexa_hash = _digest(alexa_user_id)
        row = self.repo.get_by_alexa_user(alexa_hash) or self.repo.add(AlexaLink(alexa_user_hash=alexa_hash))
        row.code_hash = _digest(code)
        row.code_expires_at = now + CODE_TTL
        self.session.commit()
        logger.info("alexa pairing code issued (link %s)", row.id)
        return code

    def redeem(self, code: str, user_id: int) -> None:
        """Link the Alexa account waiting on ``code`` to ``user_id``.

        Raises:
            AlexaPairingError: No live code matches.
        """
        digits = normalize_code(code)
        if len(digits) != CODE_DIGITS:
            raise AlexaPairingError("Enter the six-digit code Alexa read out.")
        now = _now()
        row = self.repo.find_live_code(_digest(digits), now)
        if row is None or (row.code_expires_at and _aware(row.code_expires_at) <= now):
            raise AlexaPairingError("That code didn't match. Say \"Alexa, open Enchanted Spoon\" for a new one.")
        row.user_id = user_id
        row.linked_at = now
        row.code_hash = None
        row.code_expires_at = None
        self.session.commit()
        logger.info("alexa linked by voice code for user %s", user_id)

    def connections(self, user_id: int) -> List[AlexaConnection]:
        """A user's linked Alexa accounts, for Settings."""
        return [
            AlexaConnection(connected_at=_aware(row.linked_at or row.created_at))
            for row in self.repo.linked_for_user(user_id)
        ]

    def disconnect_all(self, user_id: int) -> int:
        """Unlink every Alexa account from a user; returns how many."""
        count = self.repo.delete_for_user(user_id)
        self.session.commit()
        return count
