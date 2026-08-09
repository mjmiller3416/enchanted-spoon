"""API router for AI-powered nutrition estimation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
from app.database.db import get_session
from app.dtos.nutrition_dtos import (
    NutritionEstimationRequestDTO,
    NutritionEstimationResponseDTO,
)
from app.models.user import User
from app.services.ai.nutrition_estimation import get_nutrition_estimation_service
from app.services.usage_service import UsageService

router = APIRouter()


@router.post("", response_model=NutritionEstimationResponseDTO)
async def estimate_nutrition(
    request: NutritionEstimationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_suggestions_requested")),
) -> NutritionEstimationResponseDTO:
    """Estimate nutrition facts for a recipe using AI.

    Args:
        request: Recipe name, ingredients list, and optional servings.

    Returns:
        Estimated nutrition facts per serving.
    """
    try:
        service = get_nutrition_estimation_service()
        result = service.estimate(request)

        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error or "Nutrition estimation failed"
            )

        # Track usage (silent fail)
        try:
            UsageService(session, current_user.id).increment("ai_suggestions_requested")
        except Exception:
            pass

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Nutrition estimation failed: {str(e)}"
        )
