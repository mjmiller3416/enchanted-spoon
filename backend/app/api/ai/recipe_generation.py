"""API router for AI-powered recipe generation."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
from app.core.rate_limit import GENERATION_IP_LIMITS, GENERATION_USER_LIMITS, ip_limiter, limiter
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
from app.services.user_category_service import UserCategoryService
from app.api.errors import internal_error

router = APIRouter()

_generation_limit = require_within_usage_limit(
    "ai_suggestions_requested",
    user_limits=GENERATION_USER_LIMITS,
    ip_limits=GENERATION_IP_LIMITS,
)


@router.post("", response_model=RecipeGenerationResponseDTO)
@limiter.limit("5/minute")
@ip_limiter.limit("15/minute")
async def generate_recipe(
    request: Request,
    body: RecipeGenerationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(_generation_limit),
) -> RecipeGenerationResponseDTO:
    """Generate a complete recipe from a text prompt using AI.

    Photos are not generated here. Use POST /ai/image-generation.
    """
    del request  # required by the rate-limit decorator
    try:
        if not body.allowed_categories:
            category_service = UserCategoryService(session, current_user.id)
            user_categories = category_service.get_all_categories(include_disabled=False)
            body.allowed_categories = [cat.value for cat in user_categories]
        body.generate_image = False

        service = get_recipe_generation_service()
        result = await service.generate(body)

        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error or "Recipe generation failed"
            )

        return result

    except HTTPException:
        raise
    except RecipeParseError:
        raise internal_error("Failed to parse AI response. Please try again.")
    except RecipeGenerationError:
        raise internal_error("Recipe generation failed. Please try again.")
    except Exception:
        raise internal_error("Recipe generation failed. Please try again.")
