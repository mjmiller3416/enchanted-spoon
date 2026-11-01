"""API router for AI-powered nutrition estimation."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
from app.core.rate_limit import LIGHT_IP_LIMITS, LIGHT_USER_LIMITS, ip_limiter, limiter
from app.database.db import get_session
from app.dtos.nutrition_dtos import (
    NutritionEstimationRequestDTO,
    NutritionEstimationResponseDTO,
)
from app.models.user import User
from app.services.ai.nutrition_estimation import get_nutrition_estimation_service
from app.api.errors import internal_error

router = APIRouter()


_nutrition_limit = require_within_usage_limit(
    "ai_suggestions_requested",
    user_limits=LIGHT_USER_LIMITS,
    ip_limits=LIGHT_IP_LIMITS,
)


@router.post("", response_model=NutritionEstimationResponseDTO)
@limiter.limit("10/minute")
@ip_limiter.limit("30/minute")
async def estimate_nutrition(
    request: Request,
    body: NutritionEstimationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(_nutrition_limit),
) -> NutritionEstimationResponseDTO:
    """Estimate nutrition facts for a recipe using AI.

    Args:
        request: Recipe name, ingredients list, and optional servings.

    Returns:
        Estimated nutrition facts per serving.
    """
    del request
    try:
        service = get_nutrition_estimation_service()
        result = service.estimate(body)

        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error or "Nutrition estimation failed"
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise internal_error()
    except Exception as e:
        raise internal_error("Nutrition estimation failed. Please try again.")
