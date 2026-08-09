"""API router for AI-powered recipe generation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
from app.database.db import get_session
from app.dtos.recipe_generation_dtos import (
    RecipeGenerationRequestDTO,
    RecipeGenerationResponseDTO,
)
from app.models.user import User
from app.services.ai.recipe_generation import get_recipe_generation_service
from app.services.ai.recipe_generation.service import (
    RecipeGenerationError,
    RecipeParseError,
)
from app.services.usage_service import UsageService
from app.services.user_category_service import UserCategoryService

router = APIRouter()


@router.post("", response_model=RecipeGenerationResponseDTO)
async def generate_recipe(
    request: RecipeGenerationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_suggestions_requested")),
) -> RecipeGenerationResponseDTO:
    """Generate a complete recipe from a text prompt using AI.

    Fetches the user's enabled categories and injects them into the request
    so the AI model uses the correct category vocabulary.

    Args:
        request: User prompt, optional preferences, and feature flags.

    Returns:
        Generated recipe with optional nutrition facts and images.
    """
    try:
        # Inject user's enabled categories if not already provided
        if not request.allowed_categories:
            category_service = UserCategoryService(session, current_user.id)
            user_categories = category_service.get_all_categories(include_disabled=False)
            request.allowed_categories = [cat.value for cat in user_categories]

        service = get_recipe_generation_service()
        result = await service.generate(request)

        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error or "Recipe generation failed"
            )

        # Track usage (silent fail)
        try:
            UsageService(session, current_user.id).increment("ai_suggestions_requested")
        except Exception:
            pass

        return result

    except HTTPException:
        raise
    except RecipeParseError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse AI response: {str(e)}"
        )
    except RecipeGenerationError as e:
        raise HTTPException(
            status_code=500, detail=f"Recipe generation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Recipe generation failed: {str(e)}"
        )
