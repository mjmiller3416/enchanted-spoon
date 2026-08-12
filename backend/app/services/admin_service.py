"""app/services/admin_service.py

Service layer for admin operations. Handles user management
and database query business logic.
"""

import re
import time
from datetime import datetime
from typing import Any, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from typing import Optional

from ..dtos.admin_dtos import (
    AdminGrantProDTO,
    AdminQueryResponseDTO,
    AdminUsageResponseDTO,
    AdminUserListDTO,
    AdminUserListResponseDTO,
    AdminUserUsageDTO,
)
from ..models.user_usage import UserUsage
from ..repositories.admin_repo import AdminRepo


# ── Domain Exceptions ────────────────────────────────────────────────────────


class AdminUserNotFoundError(Exception):
    """Raised when the target user is not found."""
    pass


class CannotDeleteSelfError(Exception):
    """Raised when an admin tries to delete their own account."""
    pass


class CannotDemoteSelfError(Exception):
    """Raised when an admin tries to remove their own admin flag."""
    pass


class AdminSaveError(Exception):
    """Raised when an admin operation fails to persist."""
    pass


class AdminQueryForbiddenError(Exception):
    """Raised when a query contains non-SELECT statements."""
    pass


class AdminQueryExecutionError(Exception):
    """Raised when a SQL query fails to execute."""
    pass


_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

MAX_QUERY_ROWS = 500


# ── Admin Service ────────────────────────────────────────────────────────────


class AdminService:
    """Service for admin panel operations."""

    def __init__(self, session: Session, current_user_id: int):
        self.session = session
        self.current_user_id = current_user_id
        self.repo = AdminRepo(session)

    # ── User Management ──────────────────────────────────────────────────────

    def list_users(self, skip: int = 0, limit: int = 50) -> AdminUserListResponseDTO:
        """List all users with pagination."""
        users, total = self.repo.list_users(skip=skip, limit=limit)
        return AdminUserListResponseDTO(
            items=[AdminUserListDTO.from_model(u) for u in users],
            total=total,
        )

    def get_usage_by_user(
        self, month: Optional[str] = None
    ) -> AdminUsageResponseDTO:
        """Per-user AI feature usage for a month (defaults to current UTC month).

        Every user appears sorted by id, even with no usage row for the month
        (counters all 0). This is read-only, so no commit is performed.
        """
        resolved_month = month or UserUsage.get_current_month()
        rows = self.repo.list_usage_for_month(resolved_month)
        return AdminUsageResponseDTO(
            month=resolved_month,
            users=[
                AdminUserUsageDTO.from_models(user, usage) for user, usage in rows
            ],
        )

    def grant_pro(self, user_id: int, dto: AdminGrantProDTO) -> AdminUserListDTO:
        """Grant temporary pro access to a user."""
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise AdminUserNotFoundError(f"User {user_id} not found")

        try:
            user = self.repo.update_user_pro_grant(
                user,
                granted_pro_until=dto.granted_pro_until,
                granted_by=dto.granted_by,
            )
            self.session.commit()
            return AdminUserListDTO.from_model(user)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise AdminSaveError(f"Failed to grant pro access: {e}") from e

    def revoke_pro(self, user_id: int) -> AdminUserListDTO:
        """Revoke granted pro access from a user."""
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise AdminUserNotFoundError(f"User {user_id} not found")

        try:
            user = self.repo.revoke_user_pro_grant(user)
            self.session.commit()
            return AdminUserListDTO.from_model(user)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise AdminSaveError(f"Failed to revoke pro access: {e}") from e

    def toggle_admin(self, user_id: int, is_admin: bool) -> AdminUserListDTO:
        """Toggle admin flag on a user."""
        if user_id == self.current_user_id and not is_admin:
            raise CannotDemoteSelfError("Cannot remove your own admin access")

        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise AdminUserNotFoundError(f"User {user_id} not found")

        try:
            user = self.repo.update_user_admin_flag(user, is_admin=is_admin)
            self.session.commit()
            return AdminUserListDTO.from_model(user)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise AdminSaveError(f"Failed to toggle admin flag: {e}") from e

    def delete_user(self, user_id: int) -> None:
        """Delete a user and all their data."""
        if user_id == self.current_user_id:
            raise CannotDeleteSelfError("Cannot delete your own account")

        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise AdminUserNotFoundError(f"User {user_id} not found")

        try:
            self.repo.delete_user(user)
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise AdminSaveError(f"Failed to delete user: {e}") from e

    # ── Database Query ───────────────────────────────────────────────────────

    def execute_query(self, query: str) -> AdminQueryResponseDTO:
        """Execute a read-only SQL query and return results."""
        stripped = query.strip().rstrip(";").strip()
        if not stripped:
            raise AdminQueryForbiddenError("Query cannot be empty")

        if _FORBIDDEN_PATTERN.search(stripped):
            raise AdminQueryForbiddenError(
                "Only SELECT queries are allowed. "
                "INSERT, UPDATE, DELETE, DROP, and other write operations are forbidden."
            )

        try:
            start = time.perf_counter()
            result = self.session.execute(text(stripped))
            columns = list(result.keys())
            rows: List[List[Any]] = [
                [self._serialize_value(v) for v in row] for row in result.fetchmany(MAX_QUERY_ROWS)
            ]
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

            return AdminQueryResponseDTO(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=elapsed_ms,
            )
        except SQLAlchemyError as e:
            self.session.rollback()
            raise AdminQueryExecutionError(str(e)) from e

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Convert non-JSON-serializable values to strings."""
        if value is None:
            return None
        if isinstance(value, (int, float, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

