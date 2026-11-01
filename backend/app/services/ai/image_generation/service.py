"""Service for generating AI images using Gemini."""

from typing import Optional

from google.genai import types

from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.provider_errors import safe_ai_error
from app.services.ai.response_utils import extract_image_data
from app.services.ai.usage_logging import log_usage_metadata

from .config import (
    API_KEY_ENV_VAR,
    ASPECT_RATIO,
    BANNER_ASPECT_RATIO,
    BANNER_FROM_REFERENCE_PROMPT,
    BANNER_IMAGE_SIZE,
    FALLBACK_MODEL_NAME,
    MODEL_NAME,
    PROMPT_TEMPLATE,
    REFERENCE_IMAGE_SIZE,
)


class ImageGenerationService:
    """Service for generating recipe images using Gemini AI."""

    def __init__(self) -> None:
        """Initialize the image generation service."""
        get_gemini_client(API_KEY_ENV_VAR, retry_attempts=1, timeout_ms=120_000)

    async def generate_recipe_image(
        self,
        recipe_name: str,
        custom_prompt: Optional[str] = None,
        aspect_ratio: str = "1:1",
        image_size: Optional[str] = None,
    ) -> dict:
        """Generate an AI image for a recipe.

        Args:
            recipe_name: The name of the recipe to generate an image for.
            custom_prompt: Optional custom prompt template (must include {recipe_name}).
            aspect_ratio: Image aspect ratio (default "1:1").
            image_size: Output resolution (e.g. "1K", "2K", "4K"). None uses model default.

        Returns:
            dict with 'success', 'image_data' (base64), and optional 'error'.
        """
        if not recipe_name or not recipe_name.strip():
            return {
                "success": False,
                "image_data": None,
                "error": "Recipe name is required",
            }

        try:
            client = get_gemini_client(API_KEY_ENV_VAR, retry_attempts=1, timeout_ms=120_000)

            template = (
                custom_prompt
                if custom_prompt and "{recipe_name}" in custom_prompt
                else PROMPT_TEMPLATE
            )
            prompt = template.format(recipe_name=recipe_name.strip())
            size = image_size or REFERENCE_IMAGE_SIZE
            attempts: list[tuple[str, str]] = [(MODEL_NAME, size)]
            if MODEL_NAME != FALLBACK_MODEL_NAME:
                attempts.append((FALLBACK_MODEL_NAME, "1K"))
                attempts.append((FALLBACK_MODEL_NAME, "512"))
            elif size != "512":
                attempts.append((MODEL_NAME, "512"))

            last_error = "No image data in response"
            for model_name, attempt_size in attempts:
                try:
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(
                                aspect_ratio=aspect_ratio,
                                image_size=attempt_size,
                            ),
                        ),
                    )
                except Exception as exc:
                    last_error = safe_ai_error(exc, "ImageGeneration")
                    continue
                log_usage_metadata("image_generation", model_name, response)
                image_data = extract_image_data(response)
                if image_data:
                    return {
                        "success": True,
                        "image_data": image_data,
                        "error": None,
                    }
                last_error = "No image data in response"

            return {
                "success": False,
                "image_data": None,
                "error": last_error,
            }

        except Exception as e:
            return {
                "success": False,
                "image_data": None,
                "error": safe_ai_error(e, "ImageGeneration"),
            }

    async def generate_banner_from_reference(
        self, recipe_name: str, reference_image_bytes: bytes
    ) -> dict:
        """Generate a banner image using the reference image as visual input.

        Args:
            recipe_name: The name of the recipe.
            reference_image_bytes: The reference image as bytes.

        Returns:
            dict with 'success', 'image_data' (base64), and optional 'error'.
        """
        try:
            client = get_gemini_client(API_KEY_ENV_VAR, retry_attempts=1, timeout_ms=120_000)

            prompt = BANNER_FROM_REFERENCE_PROMPT.format(recipe_name=recipe_name.strip())

            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=reference_image_bytes, mime_type="image/png"),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=BANNER_ASPECT_RATIO,
                        image_size=BANNER_IMAGE_SIZE,
                    ),
                ),
            )

            image_data = extract_image_data(response)
            if image_data:
                return {
                    "success": True,
                    "image_data": image_data,
                    "error": None,
                }

            return {
                "success": False,
                "image_data": None,
                "error": "No image data in response",
            }

        except Exception as e:
            return {
                "success": False,
                "image_data": None,
                "error": safe_ai_error(e, "ImageGeneration"),
            }

    async def generate_dual_recipe_images(
        self, recipe_name: str, custom_prompt: Optional[str] = None
    ) -> dict:
        """Generate one square photo. Banners are cropped from it in the client.

        ``banner_image_data`` is always None. One successful photo is one
        provider image, counted as one allowance unit by the caller.
        """
        result = {
            "success": False,
            "reference_image_data": None,
            "banner_image_data": None,
            "errors": [],
        }
        ref_result = await self.generate_recipe_image(
            recipe_name,
            custom_prompt=custom_prompt or PROMPT_TEMPLATE,
            aspect_ratio=ASPECT_RATIO,
            image_size=REFERENCE_IMAGE_SIZE,
        )
        if ref_result["success"]:
            result["reference_image_data"] = ref_result["image_data"]
            result["success"] = True
        else:
            result["errors"].append(f"Reference: {ref_result.get('error')}")
        return result


# Singleton instance
_service_instance: Optional[ImageGenerationService] = None


def get_image_generation_service() -> ImageGenerationService:
    """Get the singleton instance of the image generation service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageGenerationService()
    return _service_instance
