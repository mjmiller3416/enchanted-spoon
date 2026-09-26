"""app/services/user_service.py

Service layer for User operations.
Handles business logic for user lookup, creation, and account claiming.
"""

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from ..models.user import User
from ..repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)


def starter_content_enabled() -> bool:
    """New accounts get the onboarding starter pack unless SEED_STARTER_CONTENT=false."""
    return os.getenv("SEED_STARTER_CONTENT", "true").strip().lower() not in ("false", "0", "no")


class UserService:
    """Service layer for managing users."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = UserRepo(session)

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
        2. If not found, check for claimable user:
           - Has matching email
           - Has clerk_id == "pending_claim"
        3. If claimable, claim the account by updating clerk_id
        4. If still not found, create a brand new user and seed the
           onboarding starter pack (recipes, meals, planner, shopping list)

        This enables pre-provisioning users (like Maryann) with their data
        before they actually sign up with Clerk. When they do sign in,
        their account is automatically claimed and linked.

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
            return user

        # 2. Check for claimable user (pre-provisioned account)
        claimable = self.repo.get_claimable_user(email)
        if claimable:
            # Claim the account by updating clerk_id and profile
            self.repo.update_from_clerk(claimable, clerk_id, name, avatar_url)
            self.session.commit()
            return claimable

        # 3. Create new user with default settings
        user = self.repo.create(
            clerk_id=clerk_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        self.session.commit()
        self._seed_starter_content(user)
        return user

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
