"""app/repositories/admin_repo.py

Repository layer for admin operations. Handles direct database interactions
for user management.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.user_usage import UserUsage


class AdminRepo:
    """Handles direct DB queries for admin operations."""

    def __init__(self, session: Session):
        self.session = session

    # ── User Queries ─────────────────────────────────────────────────────────

    def list_users(self, skip: int = 0, limit: int = 50) -> Tuple[List[User], int]:
        """List all users with pagination."""
        total = self.session.scalar(select(func.count(User.id)))

        stmt = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        users = list(self.session.scalars(stmt).all())
        return users, total or 0

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by internal ID."""
        stmt = select(User).where(User.id == user_id)
        return self.session.scalars(stmt).first()

    def list_usage_for_month(
        self, month: str
    ) -> List[Tuple[User, Optional[UserUsage]]]:
        """List every user with their usage row for ``month`` (if any).

        LEFT JOIN users -> user_usage on (user_id, month) so that users with
        no usage row for the requested month still appear (paired with None).
        Ordered by user id.
        """
        stmt = (
            select(User, UserUsage)
            .outerjoin(
                UserUsage,
                and_(
                    UserUsage.user_id == User.id,
                    UserUsage.month == month,
                ),
            )
            .order_by(User.id)
        )
        return [(row[0], row[1]) for row in self.session.execute(stmt).all()]

    def update_user_pro_grant(
        self,
        user: User,
        granted_pro_until: datetime,
        granted_by: str,
    ) -> User:
        """Grant pro access to a user. Flushes only."""
        user.granted_pro_until = granted_pro_until
        user.granted_by = granted_by
        self.session.flush()
        return user

    def revoke_user_pro_grant(self, user: User) -> User:
        """Revoke granted pro access from a user. Flushes only."""
        user.granted_pro_until = None
        user.granted_by = None
        self.session.flush()
        return user

    def update_user_admin_flag(self, user: User, is_admin: bool) -> User:
        """Update admin flag on a user. Flushes only."""
        user.is_admin = is_admin
        self.session.flush()
        return user

    def delete_user(self, user: User) -> None:
        """Delete a user (cascade handles related data). Flushes only."""
        self.session.delete(user)
        self.session.flush()

