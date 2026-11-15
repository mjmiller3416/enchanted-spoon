"""Turn photos of a recipe card or cookbook page into a draft recipe.

The photos are compressed in memory, sent once, and discarded. Nothing is
written to the database or to image storage. One call returns one recipe,
whether the request held 1 photo or 4.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Optional

import anyio
from google.genai import types
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from app.dtos.recipe_generation_dtos import RecipeGeneratedDTO
from app.dtos.recipe_import_dtos import RecipeImportResponseDTO
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.parse_utils import parse_recipe_dict
from app.services.ai.response_utils import extract_text_from_response
from app.services.ai.usage_logging import log_usage_metadata

from .config import (
    API_KEY_ENV_VAR,
    DEFAULT_CATEGORIES,
    MAX_OUTPUT_TOKENS,
    MAX_PHOTO_COUNT,
    MAX_PHOTO_EDGE_PX,
    MAX_PHOTO_PIXELS,
    MAX_PHOTO_SENT_BYTES,
    MAX_PHOTO_UPLOAD_BYTES,
    PHOTO_IMPORT_MODEL,
    PHOTO_PROMPT_TEMPLATE,
)
from .service import (
    RecipeImportError,
    RecipeImportNotFoundError,
    RecipeImportParseError,
)

logger = logging.getLogger(__name__)

_ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
_JPEG_QUALITIES = (85, 70, 55)


class PhotoImportImageError(RecipeImportError):
    """The upload is not a photo this import can read."""


class PhotoImportTooLargeError(PhotoImportImageError):
    """The upload exceeds the per-photo size cap."""


def prepare_recipe_photo(data: bytes) -> bytes:
    """Resize one photo to a JPEG the extractor can read.

    Camera metadata, including location, is dropped by the re-encode.
    The returned bytes are the only copy that leaves this function.

    Raises:
        PhotoImportTooLargeError: The upload exceeds the byte cap.
        PhotoImportImageError: The bytes are empty, not a supported photo,
            or still too large after compression.
    """
    if not data:
        raise PhotoImportImageError("That photo is empty.")
    if len(data) > MAX_PHOTO_UPLOAD_BYTES:
        raise PhotoImportTooLargeError("That photo is too large (10 MB max).")

    try:
        with Image.open(io.BytesIO(data)) as opened:
            if opened.format not in _ACCEPTED_FORMATS:
                raise PhotoImportImageError("Use a JPEG, PNG, or WebP photo.")
            if opened.width < 1 or opened.height < 1:
                raise PhotoImportImageError("Use a JPEG, PNG, or WebP photo.")
            if opened.width * opened.height > MAX_PHOTO_PIXELS:
                raise PhotoImportImageError("That photo is too large to read.")
            oriented = ImageOps.exif_transpose(opened)
            if oriented is None:
                raise PhotoImportImageError("Use a JPEG, PNG, or WebP photo.")
            # Copy before the file context closes the source image.
            frame = _to_rgb(oriented).copy()
    except PhotoImportImageError:
        raise
    except (UnidentifiedImageError, DecompressionBombError, OSError) as exc:
        raise PhotoImportImageError("Use a JPEG, PNG, or WebP photo.") from exc

    frame.thumbnail((MAX_PHOTO_EDGE_PX, MAX_PHOTO_EDGE_PX), Image.Resampling.LANCZOS)
    encoded = _encode_jpeg(frame)
    if len(encoded) > MAX_PHOTO_SENT_BYTES:
        raise PhotoImportImageError(
            "That photo is too large to read. Try a smaller picture."
        )
    return encoded


def _to_rgb(image: Image.Image) -> Image.Image:
    """Flatten transparency onto white and return an RGB image."""
    if image.mode == "RGB":
        return image
    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def _encode_jpeg(image: Image.Image) -> bytes:
    """Encode JPEG without EXIF, stepping quality down until it fits."""
    encoded = b""
    for quality in _JPEG_QUALITIES:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = buffer.getvalue()
        if len(encoded) <= MAX_PHOTO_SENT_BYTES:
            return encoded
    return encoded


def _prepare_all(images: list[bytes]) -> list[bytes]:
    return [prepare_recipe_photo(image) for image in images]


class PhotoImportService:
    """Extract one draft recipe from 1–4 photos. Does not save it."""

    async def import_from_photos(
        self, images: list[bytes], allowed_categories: list[str]
    ) -> RecipeImportResponseDTO:
        """Read the photos and return a draft recipe.

        Args:
            images: Raw uploads, already capped by the route. One to four.
            allowed_categories: Category vocabulary. The default list is used
                when this is empty.

        Returns:
            A successful import response with no source URL and no image bytes.
        """
        count = len(images)
        if count < 1:
            raise PhotoImportImageError("Add at least one photo.")
        if count > MAX_PHOTO_COUNT:
            raise PhotoImportImageError(
                f"You can import up to {MAX_PHOTO_COUNT} photos at a time."
            )

        prepared = await anyio.to_thread.run_sync(_prepare_all, images)
        recipe = await self._extract(prepared, allowed_categories or DEFAULT_CATEGORIES)
        logger.info(
            "photo_import outcome=extracted photos=%s upload_bytes=%s sent_bytes=%s",
            count,
            sum(len(item) for item in images),
            sum(len(item) for item in prepared),
        )
        return RecipeImportResponseDTO(
            success=True,
            recipe=recipe,
            nutrition_facts=None,
            source_url=None,
            reference_image_data=None,
            banner_image_data=None,
        )

    async def _extract(
        self, images: list[bytes], allowed_categories: list[str]
    ) -> RecipeGeneratedDTO:
        noun = "photo" if len(images) == 1 else "photos"
        target = "that photo" if len(images) == 1 else "those photos"
        prompt = PHOTO_PROMPT_TEMPLATE.format(
            photo_count=len(images),
            photo_noun=noun,
            allowed_categories="|".join(allowed_categories),
        )
        try:
            client = get_gemini_client(API_KEY_ENV_VAR)
        except ValueError as exc:
            raise RecipeImportError("Recipe photo import is not configured.") from exc

        parts: list[object] = [
            types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in images
        ]
        parts.append(prompt)
        try:
            response = client.models.generate_content(
                model=PHOTO_IMPORT_MODEL,
                contents=parts,
                config={
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "response_mime_type": "application/json",
                    "thinking_config": {"thinking_level": "minimal"},
                },
            )
        except Exception as exc:
            logger.error("[PhotoImport] Model call failed: %s", exc)
            raise RecipeImportError("Recipe photo import failed.") from exc

        log_usage_metadata("photo_import", PHOTO_IMPORT_MODEL, response)
        data = _parse_model_json(response)
        if data.get("no_recipe_found"):
            raise RecipeImportNotFoundError(
                f"No recipe was found in {target}. "
                "Try a clearer picture of the card or page."
            )
        try:
            return parse_recipe_dict(data)
        except ValueError as exc:
            logger.error("[PhotoImport] Invalid recipe data: %s", exc)
            raise RecipeImportParseError("Failed to parse recipe data from the photo") from exc


def _parse_model_json(response: object) -> dict:
    raw_text = extract_text_from_response(response)
    if not raw_text:
        raise RecipeImportError("Recipe photo import returned no recipe.")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            data, _ = json.JSONDecoder().raw_decode(raw_text.strip())
        except json.JSONDecodeError as exc:
            logger.error("[PhotoImport] JSON parse error: %s", exc)
            raise RecipeImportParseError(
                "Failed to parse recipe data from the photo"
            ) from exc

    if not isinstance(data, dict):
        raise RecipeImportParseError("Failed to parse recipe data from the photo")
    return data


_service_instance: Optional[PhotoImportService] = None


def get_photo_import_service() -> PhotoImportService:
    """Get the singleton photo import service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = PhotoImportService()
    return _service_instance
