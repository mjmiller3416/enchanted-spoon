"""API router for importing recipes from website URLs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
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
from app.services.usage_service import UsageService
from app.services.user_category_service import UserCategoryService

router = APIRouter()


@router.post("", response_model=RecipeImportResponseDTO)
async def import_recipe(
    request: RecipeImportRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("recipes_imported")),
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
    try:
        # Inject user's enabled categories if not already provided
        if not request.allowed_categories:
            category_service = UserCategoryService(session, current_user.id)
            user_categories = category_service.get_all_categories(include_disabled=False)
            request.allowed_categories = [cat.value for cat in user_categories]

        service = get_recipe_import_service()
        result = await service.import_from_url(request)

        # Track usage (silent fail)
        try:
            UsageService(session, current_user.id).increment("recipes_imported")
        except Exception:
            pass

        return result

    except HTTPException:
        raise
    except RecipeImportFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RecipeImportNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RecipeImportParseError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse imported recipe: {str(e)}"
        )
    except RecipeImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recipe import failed: {str(e)}")
