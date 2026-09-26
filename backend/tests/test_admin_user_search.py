"""Admin user search — resolves the `user #<id>` references in feedback issues."""

import pytest

from app.api.feedback import _user_ref
from app.models.user import User
from app.repositories.admin_repo import AdminRepo


@pytest.fixture()
def users(db_session):
    rows = [
        User(clerk_id="c_search_1", email="maryann@example.com", name="Maryann R"),
        User(clerk_id="c_search_2", email="mitchell@example.com", name="Mitchell"),
        User(clerk_id="c_search_3", email="guest@example.com", name=None),
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


@pytest.mark.parametrize("term", ["{id}", "#{id}", " #{id} "])
def test_search_by_id_as_cited_in_issues(db_session, users, term):
    target = users[1]

    found, total = AdminRepo(db_session).list_users(search=term.format(id=target.id))

    assert [u.id for u in found] == [target.id]
    assert total == 1


def test_search_by_email_or_name_is_case_insensitive(db_session, users):
    repo = AdminRepo(db_session)

    assert {u.email for u in repo.list_users(search="MARY")[0]} == {"maryann@example.com"}
    assert {u.email for u in repo.list_users(search="mitch")[0]} == {"mitchell@example.com"}
    assert {u.email for u in repo.list_users(search="guest@")[0]} == {"guest@example.com"}


def test_blank_search_lists_everyone(db_session, users):
    _, total = AdminRepo(db_session).list_users(search="  ")

    assert total == db_session.query(User).count()


def test_feedback_reference_links_to_admin_lookup_without_email():
    ref = _user_ref(42)

    assert ref.startswith("user #42 ")
    assert "/admin?section=users&user=42" in ref
    assert "@" not in ref
