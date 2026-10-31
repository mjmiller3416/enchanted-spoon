"""Service for generating cooking tips using Gemini."""

import logging
import re
import random
import threading
from collections import deque
from typing import Optional

from app.dtos.cooking_tip_dtos import CookingTipResponseDTO
from app.services.ai.config import GEMINI_MODEL
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.provider_errors import safe_ai_error
from app.services.ai.response_utils import extract_text_from_response
from app.services.ai.text_utils import clean_tip

logger = logging.getLogger(__name__)

# ── Model settings ───────────────────────────────────────────────────────
MODEL_NAME = GEMINI_MODEL
TEMPERATURE = 0.9  # High temperature for variety
MAX_OUTPUT_TOKENS = 150  # Constrain output length

# Environment variable for API key
API_KEY_ENV_VAR = "GEMINI_TIP_API_KEY"
API_KEY_ENV_VAR_ALT = "GEMINI_COOKING_TIP_API_KEY"  # Alternative key name

# Diverse cooking categories to randomize tip topics
TIP_CATEGORIES = [
    "grilling and barbecue",
    "baking and pastry",
    "knife skills and cutting techniques",
    "sauce making",
    "marinating and brining",
    "stir-frying and wok cooking",
    "slow cooking and braising",
    "roasting vegetables",
    "cooking with herbs and spices",
    "egg preparation",
    "pasta cooking",
    "rice and grains",
    "soup and stock making",
    "seafood preparation",
    "meat preparation and resting",
    "food storage and preservation",
    "kitchen organization",
    "flavor balancing (salt, acid, fat, heat)",
    "caramelization and browning",
    "steaming and poaching",
    "deep frying",
    "meal prep efficiency",
    "substitutions and ingredient swaps",
    "leftover transformation",
    "breakfast cooking",
    "dessert techniques",
    "food safety and temperature",
    "cast iron care",
    "fresh produce selection",
    "freezing and thawing",
    # Additional categories for more variety
    "salad and vinaigrette building",
    "bread and yeast fermentation",
    "pressure cooker and Instant Pot",
    "pantry staples and mother sauces",
    "plating and texture contrast",
    "pickling and quick ferments",
    "budget shopping and ingredient maximizing",
]

# Prompt template for generating cooking tips (category inserted at runtime)
TIP_PROMPT_TEMPLATE = """Generate a single, helpful cooking tip about {category}. The tip should be:
- Practical and actionable
- About 1-2 sentences long
- Suitable for home cooks of all skill levels
- Something specific and useful, not generic advice
- Include one concrete detail (time, temperature, ratio, or specific tool) when appropriate

Avoid overused tips like "don't overcrowd the pan", "reserve pasta water", or "pat protein dry" unless providing a truly novel angle.

Just provide the tip text directly, no prefix like "Tip:" or bullet points."""


class CookingTipService:
    """Service for generating cooking tips using Gemini AI."""

    def __init__(self) -> None:
        """Initialize the cooking tip service."""
        # Validate eagerly so we fail fast if misconfigured
        get_gemini_client(API_KEY_ENV_VAR, API_KEY_ENV_VAR_ALT)

        # Instance state for thread-safe category rotation and tip deduplication
        self._shuffled_categories: list[str] = []
        self._recent_tips: deque = deque(maxlen=50)
        self._lock = threading.Lock()

    def _get_next_category(self) -> str:
        """Get next category using shuffle bag algorithm."""
        with self._lock:
            if not self._shuffled_categories:
                self._shuffled_categories = TIP_CATEGORIES.copy()
                random.shuffle(self._shuffled_categories)
            return self._shuffled_categories.pop()

    def _normalize_tip(self, tip: str) -> str:
        """Normalize tip for comparison: lowercase, no punctuation, collapsed spaces."""
        tip = tip.lower()
        tip = re.sub(r'[^\w\s]', '', tip)
        tip = re.sub(r'\s+', ' ', tip).strip()
        return tip

    def _jaccard_similarity(self, a: str, b: str) -> float:
        """Calculate Jaccard similarity between two normalized tips."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _is_duplicate(self, tip: str) -> bool:
        """Check if tip is too similar to recent tips."""
        normalized = self._normalize_tip(tip)
        for recent in self._recent_tips:
            if self._jaccard_similarity(normalized, recent) > 0.6:
                return True
        return False

    def generate_tip(self) -> CookingTipResponseDTO:
        """Generate a random cooking tip with deduplication.

        Returns:
            CookingTipResponseDTO with success status, tip text, and optional error.
        """
        try:
            client = get_gemini_client(API_KEY_ENV_VAR, API_KEY_ENV_VAR_ALT)
            max_retries = 3

            for attempt in range(max_retries):
                # Pick a category using shuffle bag (guarantees full rotation)
                category = self._get_next_category()
                prompt = TIP_PROMPT_TEMPLATE.format(category=category)

                # Generate the tip with constrained output
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[prompt],
                    config={
                        "temperature": TEMPERATURE,
                        "max_output_tokens": MAX_OUTPUT_TOKENS,
                        "thinking_config": {"thinking_budget": 0},
                    },
                )

                # Extract the text from the response
                tip_text = extract_text_from_response(response)
                if tip_text:
                    tip_text = clean_tip(tip_text)

                    # Check for duplicate tips
                    if self._is_duplicate(tip_text):
                        logger.info(f"[ChefTip] Duplicate detected, retrying ({attempt + 1}/{max_retries})")
                        continue

                    # Track this tip to prevent future duplicates
                    normalized = self._normalize_tip(tip_text)
                    self._recent_tips.append(normalized)

                    logger.info(f"[ChefTip] Category: {category} | Generated: {tip_text[:60]}...")
                    return CookingTipResponseDTO(
                        success=True,
                        tip=tip_text,
                        error=None,
                    )

            # All retries exhausted (rare edge case)
            return CookingTipResponseDTO(
                success=False,
                tip=None,
                error="Could not generate unique tip after retries",
            )

        except Exception as e:
            return CookingTipResponseDTO(
                success=False,
                tip=None,
                error=safe_ai_error(e, "CookingTips"),
            )


# Singleton instance
_service_instance: Optional[CookingTipService] = None


def get_cooking_tip_service() -> CookingTipService:
    """Get the singleton instance of the cooking tip service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = CookingTipService()
    return _service_instance
