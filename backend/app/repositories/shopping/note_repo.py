"""app/repositories/shopping/note_repo.py

Repository for the per-user shopping list notes pad.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ...models.shopping_note import ShoppingNote


# ── Shopping Note Repository ────────────────────────────────────────────────────────────────────────────────
class ShoppingNoteRepo:
    """Repository for reading and upserting a user's shopping notes."""

    def __init__(self, session: Session, user_id: int):
        """Initialize the Shopping Note Repository.

        Args:
            session: SQLAlchemy database session
            user_id: The ID of the current user for multi-tenant isolation
        """
        self.session = session
        self.user_id = user_id

    def get_note(self) -> Optional[ShoppingNote]:
        """Return the user's notes row, or None if they have never saved notes."""
        return self.session.get(ShoppingNote, self.user_id)

    def upsert_note(self, content: str) -> ShoppingNote:
        """Create or replace the user's notes content. Flushes, never commits."""
        note = self.get_note()
        if note is None:
            note = ShoppingNote(user_id=self.user_id, content=content)
            self.session.add(note)
        else:
            note.content = content
        self.session.flush()
        self.session.refresh(note)
        return note
