"""app/services/admin_service.py

Service layer for admin operations. Handles user management
and database query business logic.
"""

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from typing import Optional

from ..dtos.admin_dtos import (
    AdminActivityResponseDTO,
    AdminActivitySummaryDTO,
    AdminGrantProDTO,
    AdminQueryResponseDTO,
    AdminUsageResponseDTO,
    AdminUserListDTO,
    AdminUserActivityDTO,
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
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE"
    r"|COPY|LOCK|VACUUM|REINDEX|CLUSTER|COMMIT|ROLLBACK|SAVEPOINT|SET|RESET|INTO|CALL|DO"
    r"|LISTEN|NOTIFY|PREPARE|ATTACH|DETACH|PRAGMA"
    # Side-effecting / file / session functions a READ ONLY transaction doesn't stop
    r"|pg_terminate_backend|pg_cancel_backend|pg_sleep\w*|pg_read_\w+|pg_ls_\w+"
    r"|lo_\w+|dblink\w*|set_config|pg_reload_conf|pg_advisory\w*)\b",
    re.IGNORECASE,
)
# The statement must be a single read: SELECT, or WITH ... SELECT
_ALLOWED_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)

# Postgres statement timeout for console queries (ms)
QUERY_TIMEOUT_MS = 5000

MAX_QUERY_ROWS = 500

# Window for the "recent" counts in the activity view
ACTIVITY_WINDOW_DAYS = 30


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; they are stored as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# ── Admin Service ────────────────────────────────────────────────────────────


class AdminService:
    """Service for admin panel operations."""

    def __init__(self, session: Session, current_user_id: int):
        self.session = session
        self.current_user_id = current_user_id
        self.repo = AdminRepo(session)

    # ── User Management ──────────────────────────────────────────────────────

    def list_users(
        self, skip: int = 0, limit: int = 50, search: Optional[str] = None
    ) -> AdminUserListResponseDTO:
        """List users with pagination, optionally filtered by id, email or name."""
        users, total = self.repo.list_users(skip=skip, limit=limit, search=search)
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

    def get_activity_by_user(
        self, now: Optional[datetime] = None
    ) -> AdminActivityResponseDTO:
        """All-time engagement per user plus totals for the admin activity view.

        Every user appears, sorted by id. ``*_recent`` counts cover the last
        ACTIVITY_WINDOW_DAYS. Read-only, so no commit is performed.
        """
        now = now or datetime.now(timezone.utc)
        since = now - timedelta(days=ACTIVITY_WINDOW_DAYS)
        week_ago = now - timedelta(days=7)

        users: List[AdminUserActivityDTO] = []
        for user, counts in self.repo.list_activity(since):
            users.append(
                AdminUserActivityDTO(
                    user_id=user.id,
                    email=user.email,
                    name=user.name,
                    is_admin=user.is_admin,
                    subscription_tier=user.subscription_tier,
                    has_pro_access=user.has_pro_access,
                    created_at=_as_utc(user.created_at),
                    last_active_at=_as_utc(user.last_active_at),
                    last_cooked_at=_as_utc(counts.pop("last_cooked_at")),
                    **{key: value or 0 for key, value in counts.items()},
                )
            )

        def active_since(cutoff: datetime) -> int:
            return sum(1 for u in users if u.last_active_at and u.last_active_at >= cutoff)

        summary = AdminActivitySummaryDTO(
            total_users=len(users),
            active_7d=active_since(week_ago),
            active_30d=active_since(since),
            new_users_30d=sum(1 for u in users if u.created_at >= since),
            recipes_recent=sum(u.recipes_recent for u in users),
            meals_cooked_recent=sum(u.meals_cooked_recent for u in users),
        )
        return AdminActivityResponseDTO(
            window_days=ACTIVITY_WINDOW_DAYS, summary=summary, users=users
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
        except Exception as e:
            # Not only SQLAlchemyError: ORM cascade problems surface as other
            # exception types and must not leave the session dirty
            self.session.rollback()
            raise AdminSaveError(f"Failed to delete user: {e}") from e

    # ── Database Query ───────────────────────────────────────────────────────

    def execute_query(self, query: str) -> AdminQueryResponseDTO:
        """Execute a read-only SQL query and return results."""
        stripped = query.strip().rstrip(";").strip()
        if not stripped:
            raise AdminQueryForbiddenError("Query cannot be empty")

        if ";" in stripped:
            raise AdminQueryForbiddenError("Run one statement at a time.")
        if not _ALLOWED_START.match(stripped) or _FORBIDDEN_PATTERN.search(stripped):
            raise AdminQueryForbiddenError(
                "Only SELECT queries are allowed. "
                "INSERT, UPDATE, DELETE, DROP, and other write operations are forbidden."
            )

        # Belt and braces behind the keyword checks: run in a fresh, read-only
        # transaction with a timeout, and always roll it back
        dialect = self.session.get_bind().dialect.name
        self.session.rollback()
        try:
            if dialect == "postgresql":
                self.session.execute(text("SET TRANSACTION READ ONLY"))
                self.session.execute(text(f"SET LOCAL statement_timeout = {QUERY_TIMEOUT_MS}"))
            elif dialect == "sqlite":
                self.session.execute(text("PRAGMA query_only = ON"))

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
            raise AdminQueryExecutionError(str(getattr(e, "orig", e)).splitlines()[0]) from e
        finally:
            self.session.rollback()
            if dialect == "sqlite":
                self.session.execute(text("PRAGMA query_only = OFF"))
                self.session.commit()

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

