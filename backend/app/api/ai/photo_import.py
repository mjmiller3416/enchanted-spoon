"""API router for importing a recipe from photos of a card or cookbook page."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_within_usage_limit
from app.api.errors import internal_error
from app.core.photo_import import photo_import_enabled
from app.core.rate_limit import GENERATION_IP_LIMITS, GENERATION_USER_LIMITS, ip_limiter, limiter
from app.database.db import get_session
from app.dtos.recipe_import_dtos import RecipeImportResponseDTO
from app.models.user import User
from app.services.ai.recipe_import.config import MAX_PHOTO_COUNT, MAX_PHOTO_UPLOAD_BYTES
from app.services.ai.recipe_import.photo import (
    PhotoImportImageError,
    PhotoImportTooLargeError,
    get_photo_import_service,
)
from app.services.ai.recipe_import.service import (
    RecipeImportError,
    RecipeImportNotFoundError,
    RecipeImportParseError,
)
from app.services.user_category_service import UserCategoryService

router = APIRouter()

_import_limit = require_within_usage_limit(
    "recipes_imported",
    user_limits=GENERATION_USER_LIMITS,
    ip_limits=GENERATION_IP_LIMITS,
)


def require_photo_import_enabled() -> None:
    """Reject the request before an import is reserved when the flag is off."""
    if not photo_import_enabled():
        raise HTTPException(status_code=404, detail="Photo import is not available.")


def _photo_import_user(
    _authenticated: User = Depends(get_current_user),
    _enabled: None = Depends(require_photo_import_enabled),
    user: User = Depends(_import_limit),
) -> User:
    """Authenticate, then the flag, then the same import cap as URL import.

    A missing token is 401 before the flag or the import unit is considered.
    One request reserves one ``recipes_imported`` unit. Photo count does not
    change that. A failure in the handler releases the unit.
    """
    del _authenticated
    return user


def _parse_categories(raw: str | None) -> list[str]:
    if raw is None:
        return []
    if len(raw) > 2000:
        raise PhotoImportImageError("Too many categories.")
    return [part.strip() for part in raw.split(",") if part.strip()][:50]


@router.post("/photo", response_model=RecipeImportResponseDTO)
@limiter.limit("5/minute")
@ip_limiter.limit("15/minute")
async def import_recipe_from_photos(
    request: Request,
    current_user: User = Depends(_photo_import_user),
    images: list[UploadFile] = File(...),
    allowed_categories: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> RecipeImportResponseDTO:
    """Turn 1 to 4 photos of a recipe card or page into a draft recipe.

    Nothing is saved. The photos are discarded after reading. One request
    counts as one recipe import, however many photos it includes.
    """
    del request
    try:
        if len(images) < 1:
            raise PhotoImportImageError("Add at least one photo.")
        if len(images) > MAX_PHOTO_COUNT:
            raise PhotoImportImageError(
                f"You can import up to {MAX_PHOTO_COUNT} photos at a time."
            )

        payloads: list[bytes] = []
        for upload in images:
            data = await upload.read(MAX_PHOTO_UPLOAD_BYTES + 1)
            if len(data) > MAX_PHOTO_UPLOAD_BYTES:
                raise PhotoImportTooLargeError("That photo is too large (10 MB max).")
            payloads.append(data)

        categories = _parse_categories(allowed_categories)
        if not categories:
            category_service = UserCategoryService(session, current_user.id)
            user_categories = category_service.get_all_categories(include_disabled=False)
            categories = [cat.value for cat in user_categories]

        service = get_photo_import_service()
        return await service.import_from_photos(payloads, categories)
    except HTTPException:
        raise
    except PhotoImportTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except PhotoImportImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RecipeImportNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RecipeImportParseError:
        raise internal_error("We couldn't read those photos. Please try again.")
    except RecipeImportError:
        raise internal_error("Import from photo failed. Please try again.")
    except Exception:
        raise internal_error("Import from photo failed. Please try again.")
