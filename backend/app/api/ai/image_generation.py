"""API router for on-demand AI photos."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.dtos.image_generation_dtos import (
    ImageGenerationRequestDTO,
    ImageGenerationResponseDTO,
    BannerGenerationRequestDTO,
)
from app.services.ai.image_generation import get_image_generation_service
from app.services.ai.image_generation.config import PROMPT_TEMPLATE, ASPECT_RATIO, REFERENCE_IMAGE_SIZE
from app.api.auth import require_within_usage_limit
from app.core.rate_limit import IMAGE_IP_LIMITS, IMAGE_USER_LIMITS, ip_limiter, limiter
from app.database.db import get_session
from app.models.user import User
from app.api.errors import internal_error

router = APIRouter()

_image_limit = require_within_usage_limit(
    "ai_images_generated",
    user_limits=IMAGE_USER_LIMITS,
    ip_limits=IMAGE_IP_LIMITS,
)


@router.post("", response_model=ImageGenerationResponseDTO)
@limiter.limit("3/minute")
@limiter.limit("15/hour")
@ip_limiter.limit("6/minute")
async def generate_recipe_image(
    request: Request,
    body: ImageGenerationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(_image_limit),
) -> ImageGenerationResponseDTO:
    """Generate one square photo. Wide banners are cropped from it in the app."""
    del session, current_user
    if body.image_type == "banner":
        raise HTTPException(
            status_code=410,
            detail="Banner images are cropped from the square photo. Use Generate photo.",
        )
    if not body.recipe_name or not body.recipe_name.strip():
        raise HTTPException(status_code=400, detail="Recipe name is required")

    try:
        service = get_image_generation_service()
        ref_result = await service.generate_recipe_image(
            body.recipe_name,
            custom_prompt=body.custom_prompt or PROMPT_TEMPLATE,
            aspect_ratio=ASPECT_RATIO,
            image_size=REFERENCE_IMAGE_SIZE,
        )
        if not ref_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=ref_result.get("error") or "Image generation failed",
            )
        return ImageGenerationResponseDTO(
            success=True,
            reference_image_data=ref_result["image_data"],
            banner_image_data=None,
            error=None,
        )
    except HTTPException:
        raise
    except ValueError:
        raise internal_error()
    except Exception:
        raise internal_error("Image generation failed. Please try again.")


@router.post("/banner")
@limiter.limit("3/minute")
@limiter.limit("15/hour")
@ip_limiter.limit("6/minute")
async def generate_banner_image(
    request: Request,
    body: BannerGenerationRequestDTO,
) -> None:
    """Retired. Banners are cropped from the square Generate photo image."""
    del request, body
    raise HTTPException(
        status_code=410,
        detail="Banner generation was removed. Crop the square photo in the app.",
    )
