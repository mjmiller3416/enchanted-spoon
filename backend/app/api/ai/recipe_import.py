"""API router for importing recipes from website URLs."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
from app.core.rate_limit import GENERATION_IP_LIMITS, GENERATION_USER_LIMITS, ip_limiter, limiter
from app.database.db import get_session
from app.dtos.recipe_import_dtos import (
    RecipeImportRequestDTO,
    RecipeImportResponseDTO,
)
from app.models.user import User
from app.services.ai.recipe_import import get_recipe_import_service
from app.services.ai.recipe_import.service import (
    RecipeImportError,
    RecipeImportFetchError,
    RecipeImportNotFoundError,
    RecipeImportParseError,
)
from app.services.user_category_service import UserCategoryService
from app.api.errors import internal_error

router = APIRouter()


_import_limit = require_within_usage_limit(
    "recipes_imported",
    user_limits=GENERATION_USER_LIMITS,
    ip_limits=GENERATION_IP_LIMITS,
)


@router.post("", response_model=RecipeImportResponseDTO)
@limiter.limit("5/minute")
@ip_limiter.limit("15/minute")
async def import_recipe(
    request: Request,
    body: RecipeImportRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(_import_limit),
) -> RecipeImportResponseDTO:
    """Import a recipe from a website URL.

    Fetches the page, extracts its structured recipe data (with an AI text
    fallback for sites without markup), and normalizes it into the app's
    recipe shape for wizard review. Nothing is saved until the user saves
    the wizard.

    Args:
        request: The URL to import, optional category vocabulary, image flag.

    Returns:
        Imported recipe with site nutrition (when published) and source photo.
    """
    del request
    try:
        # Inject user's enabled categories if not already provided
        if not body.allowed_categories:
            category_service = UserCategoryService(session, current_user.id)
            user_categories = category_service.get_all_categories(include_disabled=False)
            body.allowed_categories = [cat.value for cat in user_categories]

        service = get_recipe_import_service()
        result = await service.import_from_url(body)

        return result

    except HTTPException:
        raise
    except RecipeImportFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RecipeImportNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RecipeImportParseError as e:
        raise internal_error("Failed to parse imported recipe. Please try again.")
    except RecipeImportError as e:
        raise internal_error()
    except Exception as e:
        raise internal_error("Recipe import failed. Please try again.")
