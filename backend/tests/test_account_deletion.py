"""Self-service account deletion and admin user deletion.

Uses a real file-backed database: what matters is what survives commits.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models import (
    Ingredient,
    Meal,
    PlannerEntry,
    Recipe,
    ShoppingItem,
    UnitConversionRule,
    User,
    UserCategory,
    UserSettings,
)
from app.services import account_service as account_module
from app.services.account_service import (
    AccountDeletionBlockedError,
    AccountDeletionError,
    AccountService,
)
from app.services.admin_service import AdminService
from app.services.billing_service import StripeCustomerError
from app.services.sample_data import SampleDataService
from app.services.user_category_service import UserCategoryService

OWNED_TABLES = (Recipe, Meal, PlannerEntry, ShoppingItem, Ingredient, UserCategory, UnitConversionRule)


@pytest.fixture()
def session(tmp_path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'accounts.db'}")

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    yield s
    s.close()
    engine.dispose()


def _make_user(session: Session, n: int) -> User:
    user = User(clerk_id=f"clerk_{n}", email=f"u{n}@example.com", name=f"U{n}")
    session.add(user)
    session.commit()
    SampleDataService(session, user.id).seed()
    UserCategoryService(session, user.id).get_all_categories()
    session.add(UserSettings(user_id=user.id))
    session.add(
        UnitConversionRule(
            ingredient_name="flour", from_unit="cup", to_unit="g", factor=120.0, user_id=user.id
        )
    )
    session.commit()
    return user


def _counts(session: Session, user_id: int) -> dict:
    return {
        m.__name__: session.scalar(select(func.count()).select_from(m).where(m.user_id == user_id))
        for m in OWNED_TABLES
    }


@pytest.fixture()
def no_external_calls():
    with patch.object(account_module, "delete_clerk_user") as clerk, patch(
        "app.services.billing_service.stripe.Customer.delete"
    ) as stripe_delete, patch.object(account_module, "get_auth_settings") as auth:
        auth.return_value.auth_disabled = False
        auth.return_value.integration_user_id = None
        yield clerk, stripe_delete


class TestSelfServiceDeletion:
    def test_deletes_everything_owned_and_nothing_else(self, session, no_external_calls):
        clerk, _ = no_external_calls
        owner, other = _make_user(session, 1), _make_user(session, 2)
        other_before = _counts(session, other.id)
        owner_id = owner.id

        assert AccountService(session).delete_account(owner) is True

        session.expire_all()
        assert session.get(User, owner_id) is None
        assert not any(_counts(session, owner_id).values())
        assert session.get(UserSettings, owner_id) is None
        assert _counts(session, other.id) == other_before
        clerk.assert_called_once_with("clerk_1")

    def test_cancels_stripe_before_deleting(self, session, no_external_calls):
        _, stripe_delete = no_external_calls
        owner = _make_user(session, 1)
        owner.stripe_customer_id = "cus_123"
        session.commit()

        with patch("app.services.billing_service.get_stripe_settings") as settings:
            settings.return_value.stripe_secret_key = "sk_test"
            AccountService(session).delete_account(owner)

        stripe_delete.assert_called_once_with("cus_123")

    def test_billing_failure_deletes_nothing(self, session, no_external_calls):
        owner = _make_user(session, 1)
        before = _counts(session, owner.id)
        with patch(
            "app.services.billing_service.BillingService.delete_customer",
            side_effect=StripeCustomerError("down"),
        ):
            with pytest.raises(AccountDeletionError):
                AccountService(session).delete_account(owner)
        assert session.get(User, owner.id) is not None
        assert _counts(session, owner.id) == before

    def test_integration_account_is_protected(self, session, no_external_calls):
        owner = _make_user(session, 1)
        account_module.get_auth_settings.return_value.integration_user_id = owner.id
        with pytest.raises(AccountDeletionBlockedError):
            AccountService(session).delete_account(owner)
        assert session.get(User, owner.id) is not None

    def test_clerk_failure_still_reports_data_deleted(self, session, no_external_calls):
        clerk, _ = no_external_calls
        clerk.side_effect = account_module.ClerkApiError("down")
        owner = _make_user(session, 1)
        owner_id = owner.id
        assert AccountService(session).delete_account(owner) is False
        assert session.get(User, owner_id) is None


class TestAdminDeleteUser:
    def test_admin_can_delete_a_user_with_settings(self, session):
        admin = User(clerk_id="clerk_admin", email="admin@example.com", is_admin=True)
        session.add(admin)
        session.commit()
        target = _make_user(session, 1)
        target_id = target.id

        AdminService(session, admin.id).delete_user(target_id)

        session.expire_all()
        assert session.get(User, target_id) is None
        assert not any(_counts(session, target_id).values())
