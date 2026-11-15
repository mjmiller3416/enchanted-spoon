"""app/repositories/alexa_link_repo.py

Data access for Alexa voice pairing (``alexa_links``). Flushes only;
AlexaLinkService owns the transaction and commits.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models.alexa_link import AlexaLink


class AlexaLinkRepo:
    """Reads and writes Alexa links, always by digest or by the owning user."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_alexa_user(self, alexa_user_hash: str) -> Optional[AlexaLink]:
        """The row for one Alexa account, if any."""
        return self.session.execute(
            select(AlexaLink).where(AlexaLink.alexa_user_hash == alexa_user_hash)
        ).scalar_one_or_none()

    def find_live_code(self, code_hash: str, now: datetime) -> Optional[AlexaLink]:
        """An unlinked row waiting on this code, not yet expired."""
        return self.session.execute(
            select(AlexaLink)
            .where(AlexaLink.code_hash == code_hash)
            .where(AlexaLink.code_expires_at > now)
            .order_by(AlexaLink.id)
            .limit(1)
        ).scalar_one_or_none()

    def linked_for_user(self, user_id: int) -> List[AlexaLink]:
        """A user's linked Alexa accounts, newest first."""
        return list(
            self.session.execute(
                select(AlexaLink)
                .where(AlexaLink.user_id == user_id)
                .order_by(AlexaLink.linked_at.desc())
            ).scalars()
        )

    def add(self, link: AlexaLink) -> AlexaLink:
        """Stage a new row and flush so it has an id."""
        self.session.add(link)
        self.session.flush()
        return link

    def delete_for_user(self, user_id: int) -> int:
        """Remove every Alexa account linked to a user; returns how many."""
        result = self.session.execute(delete(AlexaLink).where(AlexaLink.user_id == user_id))
        self.session.flush()
        return result.rowcount or 0
