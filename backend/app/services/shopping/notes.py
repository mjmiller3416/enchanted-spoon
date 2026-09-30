"""app/services/shopping/notes.py

Mixin for the free-text notes pad on the shopping list.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from ...dtos.shopping_dtos import ShoppingNotesResponseDTO

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from ...repositories.shopping import ShoppingRepo


# -- Notes Mixin ---------------------------------------------------------------------------------
class NotesMixin:
    """Read and save the user's shopping list notes."""

    session: Session
    shopping_repo: ShoppingRepo

    def get_notes(self) -> ShoppingNotesResponseDTO:
        """Return the user's notes, or an empty notes DTO if none were ever saved."""
        note = self.shopping_repo.get_note()
        if note is None:
            return ShoppingNotesResponseDTO()
        return ShoppingNotesResponseDTO(content=note.content, updated_at=note.updated_at)

    def save_notes(self, content: str) -> ShoppingNotesResponseDTO:
        """Replace the user's notes with ``content`` and commit."""
        try:
            note = self.shopping_repo.upsert_note(content)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return ShoppingNotesResponseDTO(content=note.content, updated_at=note.updated_at)
