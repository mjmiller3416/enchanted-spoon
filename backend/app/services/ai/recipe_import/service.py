"""Service for importing recipes from website URLs.

Pipeline: fetch the page → extract structured recipe data (schema.org via
recipe-scrapers, works on the vast majority of recipe sites) → normalize into
the app's recipe shape with one small Gemini call. Sites without structured
markup fall back to AI extraction over the page's readable text. The source
photo is downloaded server-side and returned as base64 so it rides the same
upload path as AI-generated images.
"""

import base64
import ipaddress
import json
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_html

from app.dtos.nutrition_dtos import NutritionFactsDTO
from app.dtos.recipe_generation_dtos import RecipeGeneratedDTO
from app.dtos.recipe_import_dtos import (
    RecipeImportRequestDTO,
    RecipeImportResponseDTO,
)
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.parse_utils import parse_recipe_dict, safe_float, safe_int
from app.services.ai.response_utils import extract_text_from_response

from .config import (
    API_KEY_ENV_VAR,
    DEFAULT_CATEGORIES,
    FETCH_HEADERS,
    FETCH_TIMEOUT_SECONDS,
    MAX_FALLBACK_TEXT_CHARS,
    MAX_IMAGE_BYTES,
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    PROMPT_TEMPLATE,
    TEMPERATURE,
)

logger = logging.getLogger(__name__)


# ── Domain Exceptions ────────────────────────────────────────────────────────


class RecipeImportError(Exception):
    """Raised when recipe import fails."""

    pass


class RecipeImportFetchError(RecipeImportError):
    """Raised when the URL cannot be fetched (blocked, missing, timeout)."""

    pass


class RecipeImportNotFoundError(RecipeImportError):
    """Raised when the fetched page contains no recipe."""

    pass


class RecipeImportParseError(RecipeImportError):
    """Raised when the AI normalization response cannot be parsed."""

    pass


# ── Service ──────────────────────────────────────────────────────────────────


class RecipeImportService:
    """Service for importing recipes from website URLs."""

    def __init__(self) -> None:
        """Initialize the recipe import service."""
        get_gemini_client(API_KEY_ENV_VAR)

    async def import_from_url(
        self, request: RecipeImportRequestDTO
    ) -> RecipeImportResponseDTO:
        """Import a recipe from a website URL.

        Args:
            request: The import request with url, categories, and image flag.

        Returns:
            RecipeImportResponseDTO with the normalized recipe, site nutrition
            when published, and the source photo as base64.

        Raises:
            RecipeImportFetchError: The URL is invalid, blocked, or unreachable.
            RecipeImportNotFoundError: The page contains no recipe.
            RecipeImportParseError: The AI response cannot be parsed.
            RecipeImportError: Any other import failure.
        """
        url = self._validate_url(request.url)
        html = await self._fetch_html(url)

        extracted = self._extract_structured(html, url)
        nutrition_facts: Optional[NutritionFactsDTO] = None
        image_url: Optional[str] = None

        if extracted is not None:
            source_block = self._build_source_block(extracted)
            nutrition_facts = self._parse_site_nutrition(extracted.get("nutrients"))
            image_url = extracted.get("image")
        else:
            logger.info(f"[RecipeImport] No structured data at {url}, using text fallback")
            page_text = self._html_to_text(html)
            source_block = (
                "Raw text content of the page (extract the recipe from it):\n"
                f"{page_text}"
            )
            image_url = self._find_og_image(html)

        recipe = await self._normalize_with_ai(source_block, request.allowed_categories)

        reference_image_data: Optional[str] = None
        if request.include_source_image and image_url:
            reference_image_data = await self._download_image(image_url, url)

        logger.info(
            f"[RecipeImport] Imported '{recipe.recipe_name}' from {url} "
            f"({len(recipe.ingredients)} ingredients, "
            f"nutrition={'site' if nutrition_facts else 'none'}, "
            f"image={'yes' if reference_image_data else 'no'})"
        )

        return RecipeImportResponseDTO(
            success=True,
            recipe=recipe,
            nutrition_facts=nutrition_facts,
            source_url=url,
            reference_image_data=reference_image_data,
        )

    # ── URL validation & fetching ────────────────────────────────────────────

    @staticmethod
    def _validate_url(raw_url: str) -> str:
        """Validate the URL scheme and reject private/loopback targets.

        Basic SSRF guard: only public http(s) hosts are fetched. Hostnames that
        are IP literals in private ranges, localhost, and schemes like file://
        are rejected.
        """
        url = raw_url.strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            if "://" in url:
                raise RecipeImportFetchError("Only http(s) URLs can be imported")
            url = f"https://{url}"

        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if not hostname or "." not in hostname:
            raise RecipeImportFetchError("That doesn't look like a valid website URL")
        if hostname.lower() in ("localhost", "localhost.localdomain"):
            raise RecipeImportFetchError("That doesn't look like a valid website URL")
        try:
            ip = ipaddress.ip_address(hostname)
            if not ip.is_global:
                raise RecipeImportFetchError("That doesn't look like a valid website URL")
        except ValueError:
            pass  # hostname is a domain name, not an IP literal

        return url

    @staticmethod
    async def _fetch_html(url: str) -> str:
        """Fetch the page HTML with browser-like headers."""
        try:
            async with httpx.AsyncClient(
                headers=FETCH_HEADERS,
                follow_redirects=True,
                timeout=FETCH_TIMEOUT_SECONDS,
            ) as client:
                response = await client.get(url)
        except httpx.TimeoutException as e:
            raise RecipeImportFetchError(
                "The website took too long to respond. Please try again."
            ) from e
        except httpx.HTTPError as e:
            raise RecipeImportFetchError(
                "Could not reach that website. Check the URL and try again."
            ) from e

        if response.status_code in (401, 403):
            raise RecipeImportFetchError(
                "This website blocks automated access. Try copying the recipe manually."
            )
        if response.status_code == 404:
            raise RecipeImportFetchError("That page could not be found (404).")
        if response.status_code >= 400:
            raise RecipeImportFetchError(
                f"The website returned an error (HTTP {response.status_code})."
            )

        content_type = response.headers.get("content-type", "")
        if content_type and not any(
            t in content_type for t in ("text/html", "application/xhtml", "text/plain")
        ):
            raise RecipeImportFetchError("That URL doesn't point to a web page.")

        return response.text

    # ── Structured extraction (schema.org via recipe-scrapers) ──────────────

    @staticmethod
    def _extract_structured(html: str, url: str) -> Optional[dict]:
        """Extract recipe fields via recipe-scrapers (site handlers + schema.org).

        Returns None when the page has no usable structured recipe data, in
        which case the caller falls back to AI extraction over the page text.
        """
        try:
            scraper = scrape_html(html, org_url=url, supported_only=False)
        except Exception:
            return None

        def safe(getter_name: str):
            try:
                return getattr(scraper, getter_name)()
            except Exception:
                return None

        extracted = {
            "title": safe("title"),
            "description": safe("description"),
            "prep_time": safe("prep_time"),
            "cook_time": safe("cook_time"),
            "total_time": safe("total_time"),
            "yields": safe("yields"),
            "category": safe("category"),
            "cuisine": safe("cuisine"),
            "ingredients": safe("ingredients"),
            "instructions": safe("instructions"),
            "image": safe("image"),
            "nutrients": safe("nutrients"),
        }

        # Without these three the structured data isn't usable as a recipe
        if not (extracted["title"] and extracted["ingredients"] and extracted["instructions"]):
            return None
        return extracted

    @staticmethod
    def _build_source_block(extracted: dict) -> str:
        """Format scraped fields into the prompt's source block."""
        lines: list[str] = ["Structured recipe data extracted from the page:"]
        if extracted.get("title"):
            lines.append(f"Title: {extracted['title']}")
        if extracted.get("description"):
            lines.append(f"Description: {extracted['description']}")
        for label, key in (
            ("Prep time (minutes)", "prep_time"),
            ("Cook time (minutes)", "cook_time"),
            ("Total time (minutes)", "total_time"),
        ):
            if extracted.get(key):
                lines.append(f"{label}: {extracted[key]}")
        if extracted.get("yields"):
            lines.append(f"Yields: {extracted['yields']}")
        if extracted.get("category"):
            lines.append(f"Category: {extracted['category']}")
        if extracted.get("cuisine"):
            lines.append(f"Cuisine: {extracted['cuisine']}")
        lines.append("Ingredients:")
        lines.extend(f"- {ing}" for ing in extracted.get("ingredients") or [])
        lines.append("Instructions:")
        lines.append(extracted.get("instructions") or "")
        return "\n".join(lines)

    # ── Site nutrition ───────────────────────────────────────────────────────

    # schema.org nutrition keys → (DTO field, expected unit)
    _NUTRIENT_MAP = {
        "calories": ("calories", "kcal"),
        "proteinContent": ("protein_g", "g"),
        "fatContent": ("total_fat_g", "g"),
        "saturatedFatContent": ("saturated_fat_g", "g"),
        "transFatContent": ("trans_fat_g", "g"),
        "cholesterolContent": ("cholesterol_mg", "mg"),
        "sodiumContent": ("sodium_mg", "mg"),
        "carbohydrateContent": ("total_carbs_g", "g"),
        "fiberContent": ("dietary_fiber_g", "g"),
        "sugarContent": ("total_sugars_g", "g"),
    }

    @classmethod
    def _parse_site_nutrition(cls, nutrients: Optional[dict]) -> Optional[NutritionFactsDTO]:
        """Parse schema.org nutrition strings (e.g. '231 kcal', '35 g') into a DTO.

        Values are unit-corrected when a site publishes grams where the DTO
        expects milligrams (or vice versa). Returns None when nothing usable
        is published, leaving the wizard's AI estimation available.
        """
        if not nutrients:
            return None

        values: dict[str, float] = {}
        for source_key, (field, expected_unit) in cls._NUTRIENT_MAP.items():
            raw = nutrients.get(source_key)
            if raw is None:
                continue
            match = re.match(r"\s*([\d.]+)\s*([a-zA-Z]*)", str(raw))
            if not match:
                continue
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            unit = match.group(2).lower()
            if expected_unit == "g" and unit == "mg":
                value /= 1000
            elif expected_unit == "mg" and unit == "g":
                value *= 1000
            values[field] = value

        if not values:
            return None

        return NutritionFactsDTO(
            calories=safe_int(values.get("calories")),
            protein_g=safe_float(values.get("protein_g")),
            total_fat_g=safe_float(values.get("total_fat_g")),
            saturated_fat_g=safe_float(values.get("saturated_fat_g")),
            trans_fat_g=safe_float(values.get("trans_fat_g")),
            cholesterol_mg=safe_float(values.get("cholesterol_mg")),
            sodium_mg=safe_float(values.get("sodium_mg")),
            total_carbs_g=safe_float(values.get("total_carbs_g")),
            dietary_fiber_g=safe_float(values.get("dietary_fiber_g")),
            total_sugars_g=safe_float(values.get("total_sugars_g")),
            is_ai_estimated=False,
        )

    # ── Fallback text extraction ─────────────────────────────────────────────

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Reduce a page to readable text for the AI fallback path."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "form", "iframe"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text)
        return text[:MAX_FALLBACK_TEXT_CHARS]

    @staticmethod
    def _find_og_image(html: str) -> Optional[str]:
        """Pull the og:image URL as the photo candidate for schema-less pages."""
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", property="og:image") or soup.find(
            "meta", attrs={"name": "og:image"}
        )
        if meta and meta.get("content", "").startswith("http"):
            return meta["content"]
        return None

    # ── AI normalization ─────────────────────────────────────────────────────

    async def _normalize_with_ai(
        self, source_block: str, allowed_categories: list[str]
    ) -> RecipeGeneratedDTO:
        """Normalize scraped content into the app's recipe shape via Gemini."""
        client = get_gemini_client(API_KEY_ENV_VAR)
        categories = allowed_categories or DEFAULT_CATEGORIES

        prompt = PROMPT_TEMPLATE.format(
            source_block=source_block,
            allowed_categories="|".join(categories),
        )

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={
                    "temperature": TEMPERATURE,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "response_mime_type": "application/json",
                    "thinking_config": {"thinking_budget": 0},
                },
            )
        except Exception as e:
            logger.error(f"[RecipeImport] Gemini call failed: {e}")
            raise RecipeImportError(f"Recipe import failed: {str(e)}") from e

        raw_text = extract_text_from_response(response)
        if not raw_text:
            raise RecipeImportError("No response from AI model")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Gemini occasionally appends extra content after the JSON object;
            # fall back to decoding just the first object.
            try:
                data, _ = json.JSONDecoder().raw_decode(raw_text.strip())
            except json.JSONDecodeError as e:
                logger.error(f"[RecipeImport] JSON parse error: {e}")
                raise RecipeImportParseError(
                    "Failed to parse recipe data from AI response"
                ) from e

        if data.get("no_recipe_found"):
            raise RecipeImportNotFoundError(
                "No recipe was found on that page. Make sure the URL points directly to a recipe."
            )

        try:
            return parse_recipe_dict(data)
        except ValueError as e:
            logger.error(f"[RecipeImport] Invalid recipe data: {e}")
            raise RecipeImportParseError(str(e)) from e

    # ── Source image download ────────────────────────────────────────────────

    @staticmethod
    async def _download_image(image_url: str, page_url: str) -> Optional[str]:
        """Download the source recipe photo and return it base64-encoded.

        Failure is non-fatal — the user can still generate an image with AI
        or upload their own in the wizard.
        """
        try:
            async with httpx.AsyncClient(
                headers={**FETCH_HEADERS, "Referer": page_url},
                follow_redirects=True,
                timeout=FETCH_TIMEOUT_SECONDS,
            ) as client:
                response = await client.get(image_url)

            if response.status_code != 200:
                logger.warning(
                    f"[RecipeImport] Image download failed (HTTP {response.status_code}): {image_url}"
                )
                return None
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(f"[RecipeImport] Image URL is not an image: {image_url}")
                return None
            if len(response.content) > MAX_IMAGE_BYTES:
                logger.warning(f"[RecipeImport] Image too large, skipping: {image_url}")
                return None

            return base64.b64encode(response.content).decode("ascii")
        except Exception as e:
            logger.warning(f"[RecipeImport] Image download skipped: {e}")
            return None


# ── Singleton ────────────────────────────────────────────────────────────────

_service_instance: Optional[RecipeImportService] = None


def get_recipe_import_service() -> RecipeImportService:
    """Get the singleton instance of the recipe import service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RecipeImportService()
    return _service_instance
