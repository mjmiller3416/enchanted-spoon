"""app/api/admin.py

Admin panel API routes for user management.
All routes require admin access.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_admin
from app.database.db import get_session
from app.dtos.admin_dtos import (
    AdminGrantProDTO,
    AdminQueryRequestDTO,
    AdminQueryResponseDTO,
    AdminToggleAdminDTO,
    AdminUsageResponseDTO,
    AdminUserListDTO,
    AdminUserListResponseDTO,
)
from app.models.user import User
from app.services.admin_service import (
    AdminQueryExecutionError,
    AdminQueryForbiddenError,
    AdminSaveError,
    AdminUserNotFoundError,
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    AdminService,
)

router = APIRouter()


# ── User Management ──────────────────────────────────────────────────────────


@router.get("/users", response_model=AdminUserListResponseDTO)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> AdminUserListResponseDTO:
    """List all users with pagination."""
    service = AdminService(session, current_admin.id)
    return service.list_users(skip=skip, limit=limit)


# ── Usage Analytics ──────────────────────────────────────────────────────────


@router.get("/usage", response_model=AdminUsageResponseDTO)
def get_usage(
    month: Optional[str] = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Month in YYYY-MM format. Defaults to the current UTC month.",
    ),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> AdminUsageResponseDTO:
    """Per-user AI feature usage for a month (defaults to the current month)."""
    service = AdminService(session, current_admin.id)
    return service.get_usage_by_user(month=month)


@router.patch("/users/{user_id}/pro", response_model=AdminUserListDTO)
def grant_pro(
    user_id: int,
    dto: AdminGrantProDTO,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> AdminUserListDTO:
    """Grant temporary pro access to a user."""
    service = AdminService(session, current_admin.id)
    try:
        return service.grant_pro(user_id, dto)
    except AdminUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except AdminSaveError:
        raise HTTPException(status_code=500, detail="Failed to grant pro access")


@router.delete("/users/{user_id}/pro", response_model=AdminUserListDTO)
def revoke_pro(
    user_id: int,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> AdminUserListDTO:
    """Revoke granted pro access from a user."""
    service = AdminService(session, current_admin.id)
    try:
        return service.revoke_pro(user_id)
    except AdminUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except AdminSaveError:
        raise HTTPException(status_code=500, detail="Failed to revoke pro access")


@router.patch("/users/{user_id}/admin", response_model=AdminUserListDTO)
def toggle_admin(
    user_id: int,
    dto: AdminToggleAdminDTO,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> AdminUserListDTO:
    """Toggle admin flag on a user."""
    service = AdminService(session, current_admin.id)
    try:
        return service.toggle_admin(user_id, dto.is_admin)
    except CannotDemoteSelfError:
        raise HTTPException(
            status_code=400, detail="Cannot remove your own admin access"
        )
    except AdminUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except AdminSaveError:
        raise HTTPException(status_code=500, detail="Failed to toggle admin flag")


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> None:
    """Delete a user and all their data."""
    service = AdminService(session, current_admin.id)
    try:
        service.delete_user(user_id)
    except CannotDeleteSelfError:
        raise HTTPException(
            status_code=400, detail="Cannot delete your own account"
        )
    except AdminUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except AdminSaveError:
        raise HTTPException(status_code=500, detail="Failed to delete user")


# ── Database Query ──────────────────────────────────────────────────────────


@router.post("/query", response_model=AdminQueryResponseDTO)
def execute_query(
    dto: AdminQueryRequestDTO,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> AdminQueryResponseDTO:
    """Execute a read-only SQL query against the database."""
    service = AdminService(session, current_admin.id)
    try:
        return service.execute_query(dto.query)
    except AdminQueryForbiddenError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AdminQueryExecutionError as e:
        raise HTTPException(status_code=400, detail=f"Query error: {e}")
