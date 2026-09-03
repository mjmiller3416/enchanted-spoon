"""Admin panel DTOs for user management."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from pydantic import BaseModel, Field

from app.core.usage_limits import get_monthly_limit

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.user_usage import UserUsage


# ── Current User DTO ─────────────────────────────────────────────────────────


class CurrentUserDTO(BaseModel):
    """Response DTO for the /api/users/me endpoint."""

    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: bool
    subscription_tier: str
    subscription_status: str
    subscription_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    has_pro_access: bool
    access_reason: str

    @classmethod
    def from_model(cls, user: User) -> CurrentUserDTO:
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_admin=user.is_admin,
            subscription_tier=user.subscription_tier,
            subscription_status=user.subscription_status,
            subscription_ends_at=user.subscription_ends_at,
            cancel_at_period_end=user.cancel_at_period_end,
            has_pro_access=user.has_pro_access,
            access_reason=user.access_reason,
        )


# ── Admin User DTOs ─────────────────────────────────────────────────────────


class AdminUserListDTO(BaseModel):
    """Response DTO for a single user in admin listing."""

    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: str
    subscription_status: str
    subscription_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    is_admin: bool
    has_pro_access: bool
    access_reason: str
    granted_pro_until: Optional[datetime] = None
    granted_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user: User) -> AdminUserListDTO:
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            subscription_tier=user.subscription_tier,
            subscription_status=user.subscription_status,
            subscription_ends_at=user.subscription_ends_at,
            cancel_at_period_end=user.cancel_at_period_end,
            is_admin=user.is_admin,
            has_pro_access=user.has_pro_access,
            access_reason=user.access_reason,
            granted_pro_until=user.granted_pro_until,
            granted_by=user.granted_by,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class AdminUserListResponseDTO(BaseModel):
    """Paginated response for admin user listing."""

    items: List[AdminUserListDTO]
    total: int


class AdminGrantProDTO(BaseModel):
    """Request DTO for granting pro access to a user."""

    granted_pro_until: datetime = Field(..., description="Expiration datetime for granted pro access")
    granted_by: str = Field(..., min_length=1, max_length=100, description="Who granted access")


class AdminToggleAdminDTO(BaseModel):
    """Request DTO for toggling admin flag on a user."""

    is_admin: bool


# ── Usage-by-User DTOs ──────────────────────────────────────────────────────


class AdminUsageLimitsDTO(BaseModel):
    """Per-field monthly caps for a user. ``None`` means unlimited."""

    ai_images_generated: Optional[int] = None
    ai_suggestions_requested: Optional[int] = None
    ai_assistant_messages: Optional[int] = None
    recipes_imported: Optional[int] = None

    @classmethod
    def for_user(cls, user: User) -> AdminUsageLimitsDTO:
        """Resolve per-field caps from the user's effective tier.

        Admins are uncapped, so all their limits are ``None`` (mirrors the
        ``is_admin`` bypass in ``require_within_usage_limit``).
        """
        if user.is_admin:
            return cls()
        tier = "pro" if user.has_pro_access else "free"
        return cls(
            ai_images_generated=get_monthly_limit(tier, "ai_images_generated"),
            ai_suggestions_requested=get_monthly_limit(tier, "ai_suggestions_requested"),
            ai_assistant_messages=get_monthly_limit(tier, "ai_assistant_messages"),
            recipes_imported=get_monthly_limit(tier, "recipes_imported"),
        )


class AdminUserUsageDTO(BaseModel):
    """Response DTO for a single user's monthly AI feature usage."""

    user_id: int
    email: str
    name: Optional[str] = None
    is_admin: bool
    subscription_tier: str
    has_pro_access: bool
    ai_images_generated: int
    ai_suggestions_requested: int
    ai_assistant_messages: int
    recipes_imported: int
    recipes_created: int
    limits: AdminUsageLimitsDTO

    @classmethod
    def from_models(
        cls, user: User, usage: Optional[UserUsage]
    ) -> AdminUserUsageDTO:
        """Build the DTO from a user and its (possibly missing) usage row.

        Counters default to 0 when the user has no ``UserUsage`` row for the
        requested month. Limits are resolved from the user's effective tier
        via ``AdminUsageLimitsDTO.for_user``.
        """
        limits = AdminUsageLimitsDTO.for_user(user)

        return cls(
            user_id=user.id,
            email=user.email,
            name=user.name,
            is_admin=user.is_admin,
            subscription_tier=user.subscription_tier,
            has_pro_access=user.has_pro_access,
            ai_images_generated=usage.ai_images_generated if usage else 0,
            ai_suggestions_requested=usage.ai_suggestions_requested if usage else 0,
            ai_assistant_messages=usage.ai_assistant_messages if usage else 0,
            recipes_imported=usage.recipes_imported if usage else 0,
            recipes_created=usage.recipes_created if usage else 0,
            limits=limits,
        )


class AdminUsageResponseDTO(BaseModel):
    """Response DTO for the /api/admin/usage endpoint."""

    month: str
    users: List[AdminUserUsageDTO]


class CurrentUserUsageDTO(BaseModel):
    """Response DTO for /api/users/me/usage — the settings usage meter."""

    month: str
    ai_images_generated: int
    ai_suggestions_requested: int
    ai_assistant_messages: int
    recipes_imported: int
    limits: AdminUsageLimitsDTO

    @classmethod
    def from_models(cls, user: User, usage: UserUsage) -> CurrentUserUsageDTO:
        return cls(
            month=usage.month,
            ai_images_generated=usage.ai_images_generated or 0,
            ai_suggestions_requested=usage.ai_suggestions_requested or 0,
            ai_assistant_messages=usage.ai_assistant_messages or 0,
            recipes_imported=usage.recipes_imported or 0,
            limits=AdminUsageLimitsDTO.for_user(user),
        )


# ── Database Query DTOs ─────────────────────────────────────────────────────


class AdminQueryRequestDTO(BaseModel):
    """Request DTO for executing a read-only SQL query."""

    query: str = Field(..., min_length=1, max_length=10000)


class AdminQueryResponseDTO(BaseModel):
    """Response DTO for SQL query results."""

    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
