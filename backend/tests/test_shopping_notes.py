"""Tests for the shopping list notes pad."""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.dtos.shopping_dtos import SHOPPING_NOTES_MAX_LENGTH, ShoppingNotesUpdateDTO
from app.models.shopping_note import ShoppingNote
from app.models.user import User
from app.services.shopping import ShoppingService


def test_notes_empty_before_first_save(db_session: Session, test_user: User):
    notes = ShoppingService(db_session, test_user.id).get_notes()
    assert notes.content == ""
    assert notes.updated_at is None


def test_save_creates_then_replaces(db_session: Session, test_user: User):
    service = ShoppingService(db_session, test_user.id)

    first = service.save_notes("Costco run on Saturday")
    assert first.content == "Costco run on Saturday"
    assert first.updated_at is not None

    service.save_notes("Check for the big olive oil")
    assert service.get_notes().content == "Check for the big olive oil"
    assert db_session.query(ShoppingNote).filter_by(user_id=test_user.id).count() == 1


def test_notes_are_isolated_per_user(db_session: Session, test_user: User, second_user: User):
    ShoppingService(db_session, test_user.id).save_notes("mine")
    assert ShoppingService(db_session, second_user.id).get_notes().content == ""


def test_notes_deleted_with_user(db_session: Session, test_user: User):
    ShoppingService(db_session, test_user.id).save_notes("gone soon")
    user_id = test_user.id
    db_session.delete(test_user)
    db_session.commit()
    assert db_session.get(ShoppingNote, user_id) is None


def test_notes_length_limit():
    ShoppingNotesUpdateDTO(content="x" * SHOPPING_NOTES_MAX_LENGTH)
    with pytest.raises(ValidationError):
        ShoppingNotesUpdateDTO(content="x" * (SHOPPING_NOTES_MAX_LENGTH + 1))
