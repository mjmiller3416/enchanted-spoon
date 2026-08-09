"""API router for AI image generation."""

import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dtos.image_generation_dtos import (
    ImageGenerationRequestDTO,
    ImageGenerationResponseDTO,
    BannerGenerationRequestDTO,
    BannerGenerationResponseDTO,
)
from app.services.ai.image_generation import get_image_generation_service
from app.services.ai.image_generation.config import (
    PROMPT_TEMPLATE,
    BANNER_PROMPT_TEMPLATE,
    ASPECT_RATIO,
    BANNER_ASPECT_RATIO,
    REFERENCE_IMAGE_SIZE,
    BANNER_IMAGE_SIZE,
)
from app.api.auth import require_within_usage_limit
from app.database.db import get_session
from app.models.user import User
from app.services.usage_service import UsageService

router = APIRouter()


@router.post("", response_model=ImageGenerationResponseDTO)
async def generate_recipe_image(
    request: ImageGenerationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_images_generated")),
) -> ImageGenerationResponseDTO:
    """
    Generate an AI image for a recipe based on its name.

    The image is generated using Gemini AI with a professional food photography style.

    Args:
        request: Request containing the recipe name

    Returns:
        Response with base64 encoded image data on success
    """
    if not request.recipe_name or not request.recipe_name.strip():
        raise HTTPException(status_code=400, detail="Recipe name is required")

    try:
        service = get_image_generation_service()

        if request.image_type == "both":
            result = await service.generate_dual_recipe_images(
                request.recipe_name,
                custom_prompt=request.custom_prompt,
            )
            if not result["success"]:
                errors = result.get("errors", [])
                raise HTTPException(
                    status_code=500,
                    detail="; ".join(errors) if errors else "Image generation failed",
                )
            reference_data = result.get("reference_image_data")
            banner_data = result.get("banner_image_data")

        elif request.image_type == "reference":
            ref_result = await service.generate_recipe_image(
                request.recipe_name,
                custom_prompt=request.custom_prompt or PROMPT_TEMPLATE,
                aspect_ratio=ASPECT_RATIO,
                image_size=REFERENCE_IMAGE_SIZE,
            )
            if not ref_result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=ref_result.get("error") or "Reference image generation failed",
                )
            reference_data = ref_result["image_data"]
            banner_data = None

        else:  # banner
            banner_result = await service.generate_recipe_image(
                request.recipe_name,
                custom_prompt=request.custom_prompt or BANNER_PROMPT_TEMPLATE,
                aspect_ratio=BANNER_ASPECT_RATIO,
                image_size=BANNER_IMAGE_SIZE,
            )
            if not banner_result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=banner_result.get("error") or "Banner image generation failed",
                )
            reference_data = None
            banner_data = banner_result["image_data"]

        # Track usage (silent fail - don't break AI feature for tracking issues)
        try:
            UsageService(session, current_user.id).increment("ai_images_generated")
        except Exception:
            pass

        return ImageGenerationResponseDTO(
            success=True,
            reference_image_data=reference_data,
            banner_image_data=banner_data,
            error=None,
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Configuration errors (e.g., missing API key)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.post("/banner", response_model=BannerGenerationResponseDTO)
async def generate_banner_image(
    request: BannerGenerationRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_images_generated")),
) -> BannerGenerationResponseDTO:
    """
    Generate a banner (21:9) image from an existing reference image.

    Uses the reference image as visual input to create a wider banner version
    that maintains the same food presentation and styling.

    Args:
        request: Request containing recipe name and base64 encoded reference image

    Returns:
        Response with base64 encoded banner image data on success
    """
    if not request.recipe_name or not request.recipe_name.strip():
        raise HTTPException(status_code=400, detail="Recipe name is required")

    if not request.reference_image_data:
        raise HTTPException(status_code=400, detail="Reference image data is required")

    try:
        service = get_image_generation_service()

        # Decode base64 reference image to bytes
        reference_bytes = base64.b64decode(request.reference_image_data)

        result = await service.generate_banner_from_reference(
            request.recipe_name, reference_bytes
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error") or "Banner generation failed",
            )

        # Track usage (silent fail - don't break AI feature for tracking issues)
        try:
            UsageService(session, current_user.id).increment("ai_images_generated")
        except Exception:
            pass

        return BannerGenerationResponseDTO(
            success=True,
            banner_image_data=result.get("image_data"),
            error=None,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Banner generation failed: {str(e)}")
