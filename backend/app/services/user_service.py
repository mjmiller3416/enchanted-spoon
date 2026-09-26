"""app/services/user_service.py

Service layer for User operations.
Handles business logic for user lookup, creation, and account claiming.
"""

import logging
import os
from typing import Callable, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.user import User
from ..repositories.user_repo import UserRepo
from .clerk_service import clerk_user_has_verified_email

logger = logging.getLogger(__name__)


class AccountLinkError(Exception):
    """An existing account uses this email, but ownership couldn't be confirmed."""


def starter_content_enabled() -> bool:
    """New accounts get the onboarding starter pack unless SEED_STARTER_CONTENT=false."""
    return os.getenv("SEED_STARTER_CONTENT", "true").strip().lower() not in ("false", "0", "no")


class UserService:
    """Service layer for managing users."""

    def __init__(
        self,
        session: Session,
        email_verifier: Callable[[str, str], bool] = clerk_user_has_verified_email,
    ):
        self.session = session
        self.repo = UserRepo(session)
        # (clerk_id, email) -> is that email verified on that Clerk user?
        self._email_verifier = email_verifier

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.

        Args:
            user_id: The internal database ID.

        Returns:
            User if found, None otherwise.
        """
        return self.repo.get_by_id(user_id)

    def get_or_create_from_clerk(
        self,
        clerk_id: str,
        email: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Get existing user or create new one from Clerk token data.

        This implements the full authentication flow:

        1. Look up by clerk_id (fast path for returning users)
        2. If not found, look up by email and relink the account to the
           new clerk_id
        3. If still not found, create a brand new user and seed the
           onboarding starter pack (recipes, meals, planner, shopping list)

        Email relinking covers two cases:
        - Pre-provisioned users (clerk_id == "pending_claim", like Maryann)
          claiming their data on first sign-in.
        - Existing users arriving with a new Clerk user ID, e.g. after
          moving from the Clerk development instance to production.

        The email claim alone is not proof of ownership (it comes from a
        configurable session-token template), so a relink only happens after
        the Clerk Backend API confirms the address is *verified* on the
        signing-in Clerk user. Otherwise AccountLinkError is raised and the
        existing account is left untouched.

        Args:
            clerk_id: Clerk user ID from JWT 'sub' claim.
            email: User's email from JWT.
            name: Optional name from JWT.
            avatar_url: Optional avatar URL from JWT.

        Returns:
            The authenticated User (existing, claimed, or newly created).
        """
        # 1. Direct lookup by clerk_id (most common case)
        user = self.repo.get_by_clerk_id(clerk_id)
        if user:
            self._sync_email(user, email)
            return user

        # 2. Relink an existing account by email (pre-provisioned or new Clerk ID)
        existing = self.repo.get_by_email(email)
        if existing:
            if not self._email_verifier(clerk_id, email):
                logger.warning(
                    "Refused relink of user id=%s to clerk_id=%s: email not verified on that Clerk user",
                    existing.id, clerk_id,
                )
                raise AccountLinkError(email)
            logger.info(
                "Relinking user id=%s from clerk_id=%s to %s",
                existing.id, existing.clerk_id, clerk_id,
            )
            self.repo.update_from_clerk(existing, clerk_id, name, avatar_url)
            self.session.commit()
            return existing

        # 3. Create new user with default settings
        try:
            user = self.repo.create(
                clerk_id=clerk_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
            )
            self.session.commit()
        except IntegrityError:
            # A parallel first request for this sign-in created the row first
            self.session.rollback()
            user = self.repo.get_by_clerk_id(clerk_id)
            if user is None:
                raise
            return user

        self._seed_starter_content(user)
        return user

    def _sync_email(self, user: User, email: str) -> None:
        """
        Keep the stored email current when it changes in Clerk.

        A stale email would otherwise let whoever registers the old address
        later be offered this account on relink. Best-effort: skipped if
        another account already holds the new address.
        """
        if not email or (user.email or "").lower() == email.lower():
            return
        holder = self.repo.get_by_email(email)
        if holder is not None and holder.id != user.id:
            return
        user.email = email
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()

    def _seed_starter_content(self, user: User) -> None:
        """Best-effort: a seeding failure must never block sign-in."""
        if not starter_content_enabled():
            return

        from .sample_data import SampleDataService

        try:
            SampleDataService(self.session, user.id).seed()
        except Exception:
            self.session.rollback()
            logger.exception("Failed to seed starter content for user %s", user.id)
