"""app/services/account_service.py

Self-service account deletion: cancel billing, remove every row and owned
image the account has, then remove the sign-in identity from Clerk.
"""

import logging

from sqlalchemy.orm import Session

from ..core.auth_config import get_auth_settings
from ..models.user import User
from .billing_service import BillingService, StripeCustomerError, StripeNotConfiguredError
from .clerk_service import ClerkApiError, delete_clerk_user
from .data_management import DataManagementService

logger = logging.getLogger(__name__)


class AccountDeletionBlockedError(Exception):
    """The account can't be self-deleted (e.g. it backs a household integration)."""


class AccountDeletionError(Exception):
    """A step that must succeed before any data is removed failed."""


class AccountService:
    """Service for operations on the signed-in user's own account."""

    def __init__(self, session: Session):
        self.session = session

    def delete_account(self, user: User) -> bool:
        """
        Permanently delete ``user`` and everything they own.

        Order matters:
        1. Cancel billing first; if that fails nothing is deleted, so a user
           is never left with a live subscription and no account.
        2. Delete their data and owned Cloudinary images.
        3. Delete the user row (settings, categories, usage, etc. cascade).
        4. Delete the Clerk identity. Best-effort: the app data is already
           gone, and signing in again would only start a fresh, empty account.

        Returns:
            Whether the Clerk identity was deleted too.

        Raises:
            AccountDeletionBlockedError: The account backs a household integration.
            AccountDeletionError: Billing could not be cancelled.
        """
        settings = get_auth_settings()
        if settings.integration_user_id is not None and user.id == settings.integration_user_id:
            raise AccountDeletionBlockedError(
                "This account is connected to household apps and can't be deleted here."
            )

        try:
            BillingService(self.session).delete_customer(user)
        except (StripeNotConfiguredError, StripeCustomerError) as e:
            raise AccountDeletionError(
                "We couldn't cancel your subscription, so nothing was deleted. "
                "Please try again or contact support."
            ) from e

        user_id, clerk_id = user.id, user.clerk_id

        # Commits the data delete, then destroys owned images
        DataManagementService(self.session, user_id).clear_all_data(delete_images=True)

        try:
            self.session.delete(user)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        logger.info("Deleted account user_id=%s", user_id)

        if not clerk_id or clerk_id == "pending_claim" or settings.auth_disabled:
            return False
        try:
            delete_clerk_user(clerk_id)
            return True
        except ClerkApiError:
            logger.exception("Account %s deleted but Clerk user %s was not", user_id, clerk_id)
            return False
