"""Service for generating AI images using Gemini."""

import base64
from typing import Optional

from google.genai import types

from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.provider_errors import safe_ai_error
from app.services.ai.response_utils import extract_image_data

from .config import (
    PROMPT_TEMPLATE,
    BANNER_PROMPT_TEMPLATE,
    BANNER_FROM_REFERENCE_PROMPT,
    MODEL_NAME,
    ASPECT_RATIO,
    BANNER_ASPECT_RATIO,
    REFERENCE_IMAGE_SIZE,
    BANNER_IMAGE_SIZE,
    API_KEY_ENV_VAR,
)


class ImageGenerationService:
    """Service for generating recipe images using Gemini AI."""

    def __init__(self) -> None:
        """Initialize the image generation service."""
        get_gemini_client(API_KEY_ENV_VAR)

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
            client = get_gemini_client(API_KEY_ENV_VAR)

            template = (
                custom_prompt
                if custom_prompt and "{recipe_name}" in custom_prompt
                else PROMPT_TEMPLATE
            )
            prompt = template.format(recipe_name=recipe_name.strip())

            image_config_kwargs = {"aspect_ratio": aspect_ratio}
            if image_size:
                image_config_kwargs["image_size"] = image_size

            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(**image_config_kwargs),
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
            client = get_gemini_client(API_KEY_ENV_VAR)

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
        """Generate both reference (1:1) and banner (21:9) images for a recipe.

        Args:
            recipe_name: The name of the recipe to generate images for.
            custom_prompt: Optional custom prompt template (must include {recipe_name}).

        Returns:
            dict with 'success', 'reference_image_data', 'banner_image_data', and 'errors'.
        """
        result = {
            "success": False,
            "reference_image_data": None,
            "banner_image_data": None,
            "errors": [],
        }

        # Generate reference image (1:1 square)
        ref_result = await self.generate_recipe_image(
            recipe_name,
            custom_prompt=custom_prompt or PROMPT_TEMPLATE,
            aspect_ratio=ASPECT_RATIO,
            image_size=REFERENCE_IMAGE_SIZE,
        )
        if ref_result["success"]:
            result["reference_image_data"] = ref_result["image_data"]
        else:
            result["errors"].append(f"Reference: {ref_result.get('error')}")

        # Generate banner image using reference image as input (if available)
        if ref_result["success"]:
            reference_bytes = base64.b64decode(ref_result["image_data"])
            banner_result = await self.generate_banner_from_reference(
                recipe_name, reference_bytes
            )
        else:
            banner_result = await self.generate_recipe_image(
                recipe_name,
                custom_prompt=BANNER_PROMPT_TEMPLATE,
                aspect_ratio=BANNER_ASPECT_RATIO,
                image_size=BANNER_IMAGE_SIZE,
            )

        if banner_result["success"]:
            result["banner_image_data"] = banner_result["image_data"]
        else:
            result["errors"].append(f"Banner: {banner_result.get('error')}")

        result["success"] = bool(
            result["reference_image_data"] or result["banner_image_data"]
        )

        return result


# Singleton instance
_service_instance: Optional[ImageGenerationService] = None


def get_image_generation_service() -> ImageGenerationService:
    """Get the singleton instance of the image generation service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageGenerationService()
    return _service_instance
