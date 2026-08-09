"""app/repositories/user_repo.py

Repository layer for User model. Handles all direct database interactions
related to users, including lookup, creation, and account claiming.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.user_settings import UserSettings


class UserRepo:
    """Handles direct DB queries for the User model."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.

        Args:
            user_id: The internal database ID.

        Returns:
            User if found, None otherwise.
        """
        stmt = select(User).where(User.id == user_id)
        return self.session.scalars(stmt).first()

    def get_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        """
        Get user by Clerk external ID.

        This is the primary lookup method for authenticated requests,
        as the JWT contains the clerk_id in the 'sub' claim.

        Args:
            clerk_id: The Clerk user ID (e.g., "user_abc123").

        Returns:
            User if found, None otherwise.
        """
        stmt = select(User).where(User.clerk_id == clerk_id)
        return self.session.scalars(stmt).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address.

        Returns:
            User if found, None otherwise.
        """
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()

    def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[User]:
        """
        Get user by Stripe customer ID.

        Used by the Stripe webhook handler to resolve incoming events
        (which identify the customer, not the internal user ID) to a User.

        Args:
            stripe_customer_id: The Stripe customer ID (e.g., "cus_abc123").

        Returns:
            User if found, None otherwise.
        """
        stmt = select(User).where(User.stripe_customer_id == stripe_customer_id)
        return self.session.scalars(stmt).first()

    def get_claimable_user(self, email: str) -> Optional[User]:
        """
        Find a user that can be claimed by a new Clerk account.

        A claimable user has:
        - Matching email address
        - clerk_id == "pending_claim" (pre-provisioned user)

        This enables the scenario where an existing user (like Maryann)
        has data pre-loaded before they sign up with Clerk.

        Args:
            email: Email address from the Clerk JWT.

        Returns:
            User if claimable, None otherwise.
        """
        stmt = select(User).where(
            User.email == email,
            User.clerk_id == "pending_claim"
        )
        return self.session.scalars(stmt).first()

    def create(
        self,
        clerk_id: str,
        email: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Create a new user with default settings.

        Args:
            clerk_id: Clerk user ID from JWT.
            email: User's email address.
            name: Optional display name.
            avatar_url: Optional avatar image URL.

        Returns:
            The newly created User (not yet committed).
        """
        user = User(
            clerk_id=clerk_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            is_admin=False,
            subscription_tier="free",
        )
        self.session.add(user)
        self.session.flush()  # Get user.id for settings FK

        # Create default user settings
        settings = UserSettings(user_id=user.id)
        self.session.add(settings)

        return user

    def update_from_clerk(
        self,
        user: User,
        clerk_id: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Update user with data from Clerk token.

        Used for:
        1. Claiming a pre-provisioned account (pending_claim -> real clerk_id)
        2. Syncing profile changes from Clerk

        Args:
            user: The user to update.
            clerk_id: New Clerk ID to set.
            name: Optional name to update (only if provided).
            avatar_url: Optional avatar URL to update (only if provided).

        Returns:
            The updated User (not yet committed).
        """
        user.clerk_id = clerk_id
        if name is not None:
            user.name = name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        return user

    def update_subscription(
        self,
        user: User,
        *,
        stripe_customer_id: Optional[str] = None,
        subscription_tier: Optional[str] = None,
        subscription_status: Optional[str] = None,
        subscription_ends_at: Optional[datetime] = None,
    ) -> User:
        """
        Update a user's subscription state from a Stripe webhook event.

        Only fields explicitly passed (non-None) are updated, so handlers can
        set exactly the fields present on a given Stripe event without
        clobbering unrelated state.

        Args:
            user: The user to update.
            stripe_customer_id: Stripe customer ID to associate with this user.
            subscription_tier: New subscription tier (e.g. "free", "pro").
            subscription_status: New subscription status (e.g. "active", "canceled").
            subscription_ends_at: When the current subscription period/access ends.

        Returns:
            The updated User (not yet committed).
        """
        if stripe_customer_id is not None:
            user.stripe_customer_id = stripe_customer_id
        if subscription_tier is not None:
            user.subscription_tier = subscription_tier
        if subscription_status is not None:
            user.subscription_status = subscription_status
        if subscription_ends_at is not None:
            user.subscription_ends_at = subscription_ends_at
        self.session.flush()
        return user

    def get_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Get user settings by user ID.

        Args:
            user_id: The internal database user ID.

        Returns:
            UserSettings if found, None otherwise.
        """
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return self.session.scalars(stmt).first()

    def get_or_create_settings(self, user_id: int) -> UserSettings:
        """
        Get user settings, creating with defaults if they don't exist.

        This ensures a user always has a settings record, which simplifies
        downstream code that needs to read or update settings.

        Args:
            user_id: The internal database user ID.

        Returns:
            UserSettings (existing or newly created with defaults).
        """
        settings = self.get_settings(user_id)
        if settings is not None:
            return settings

        # Create with defaults (UserSettings model handles default values)
        settings = UserSettings(user_id=user_id)
        self.session.add(settings)
        self.session.flush()
        return settings
