"""Block create, plan, and AI writes for read-only accounts."""

from fastapi import Depends, HTTPException, Request, status

from app.api.auth.dependencies import get_current_user
from app.models.user import User

_LOCKED_PREFIXES = (
    "/api/recipes",
    "/api/meals",
    "/api/planner",
    "/api/shopping",
    "/api/upload",
    "/api/sample-data",
    "/api/recipe-groups",
    "/api/ingredients",
    "/api/ingredient-categories",
    "/api/ingredient-units",
    "/api/categories",
    "/api/unit-conversions",
    "/api/data-management",
)


def reject_read_only_writes(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """Allow GET/HEAD (view and export). Block mutations and every AI call."""
    if getattr(user, "is_read_only", False) is not True:
        return
    path = request.url.path
    method = request.method.upper()
    if path.startswith("/api/ai"):
        _deny()
    if method in {"GET", "HEAD", "OPTIONS"}:
        return
    if any(path.startswith(prefix) for prefix in _LOCKED_PREFIXES):
        _deny()


def _deny() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "read_only",
            "message": (
                "This account is read-only. You can still view and export. "
                "Creating, planning, and AI need Pro."
            ),
        },
    )
