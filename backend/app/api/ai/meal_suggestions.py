"""API router for meal-specific AI suggestions."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.dtos.meal_suggestions_dtos import MealSuggestionsRequestDTO, MealSuggestionsResponseDTO
from app.services.ai.meal_suggestions import get_meal_suggestions_service
from app.api.auth import require_within_usage_limit
from app.core.rate_limit import LIGHT_IP_LIMITS, LIGHT_USER_LIMITS, ip_limiter, limiter
from app.database.db import get_session
from app.models.user import User
from app.api.errors import internal_error

router = APIRouter()


_meal_limit = require_within_usage_limit(
    "ai_suggestions_requested",
    user_limits=LIGHT_USER_LIMITS,
    ip_limits=LIGHT_IP_LIMITS,
)


@router.post("", response_model=MealSuggestionsResponseDTO)
@limiter.limit("10/minute")
@ip_limiter.limit("30/minute")
async def get_meal_suggestions(
    request: Request,
    body: MealSuggestionsRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(_meal_limit),
) -> MealSuggestionsResponseDTO:
    """
    Get AI-generated side dish suggestions and cooking tip for a meal.

    Args:
        request: The meal details to generate suggestions for

    Returns:
        Response with side dish suggestions and cooking tip on success
    """
    del request
    try:
        service = get_meal_suggestions_service()
        result = service.generate_suggestions(body)

        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error or "Suggestions generation failed"
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise internal_error()
    except Exception as e:
        raise internal_error("Suggestions generation failed. Please try again.")
