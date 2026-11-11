"""Configuration for the Recipe Import AI service."""

from app.services.ai.config import GEMINI_LITE_MODEL
from app.services.ai.recipe_generation.config import DEFAULT_CATEGORIES

# Model settings. Gemini 3.x is called at its default temperature.
MODEL_NAME = GEMINI_LITE_MODEL
MAX_OUTPUT_TOKENS = 8192

# Environment variable for API key (reuses the recipe generation key)
API_KEY_ENV_VAR = "GEMINI_RECIPE_GENERATION_API_KEY"

# Re-exported so the route/service only import from this config
DEFAULT_CATEGORIES = DEFAULT_CATEGORIES

# ── Fetching ─────────────────────────────────────────────────────────────────

FETCH_TIMEOUT_SECONDS = 15.0
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB cap on downloaded source photos
# Page text sent to Gemini when the site has no schema.org recipe markup
MAX_FALLBACK_TEXT_CHARS = 15000

# Realistic browser headers — many recipe sites reject default client UAs
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Normalization prompt ─────────────────────────────────────────────────────
# Same JSON contract as recipe generation (parse_recipe_dict-compatible) so both
# flows share parsing. {source_block} is either structured scraped fields or raw
# page text; the model must convert faithfully, never invent.
PROMPT_TEMPLATE = """You are a data normalizer for a recipe app. Below is recipe content taken from a web page. Convert it FAITHFULLY into the app's JSON format. Do not invent, add, or omit ingredients or steps — preserve the original recipe as closely as possible while fitting the required fields.

{source_block}

Return ONLY valid JSON with this exact structure:
{{
  "recipe_name": "<the recipe's name from the page>",
  "description": "<1-2 sentence description, from the page if available>",
  "recipe_category": "<one of: {allowed_categories}>",
  "meal_type": "<one of: appetizer|breakfast|lunch|dinner|dessert|side|snack|sauce|other>",
  "diet_pref": "<one of: none|vegetarian|vegan|gluten-free|dairy-free|keto|paleo>",
  "prep_time": <integer minutes or null>,
  "cook_time": <integer minutes or null>,
  "difficulty": "<one of: Easy|Medium|Hard>",
  "servings": <integer or null>,
  "ingredients": [
    {{"ingredient_name": "Ingredient Name", "ingredient_category": "<category>", "quantity": <float or null>, "unit": "<unit or null>"}}
  ],
  "directions": "<Step one.\\nStep two.\\nStep three.>",
  "notes": "<optional tips from the page, or null>"
}}

Rules:
- Include EVERY ingredient from the source, names in Title Case, preparation hints (e.g. "sifted", "chopped") dropped from the name
- Split each ingredient line into quantity (float, e.g. 0.5), unit, and name; if an amount has no clean unit match, pick the closest allowed unit or null
- ingredient_category must be one of: produce|dairy|deli|meat|condiments|oils-and-vinegars|seafood|pantry|spices|frozen|bakery|baking|beverages|other
- unit must be one of: tbs|tsp|cup|oz|lbs|stick|bag|box|can|jar|package|piece|slice|whole|pinch|dash|to-taste
- Keep every direction step from the source, separated by \\n (no step numbers)
- If only a total time is given, put it in cook_time and leave prep_time null
- diet_pref: use "none" unless the recipe is clearly dietary
- difficulty: estimate from the number of steps and techniques
- If the content contains NO recipe at all, return exactly: {{"no_recipe_found": true}}"""

# ── Photo import ─────────────────────────────────────────────────────────────
# Pinned literal. URL import follows GEMINI_LITE_MODEL (env-overridable).
# Photo import does not, so another lite-model override cannot change this path.
PHOTO_IMPORT_MODEL = "gemini-3.1-flash-lite"
# One request, one recipe, however many pages were attached.
MAX_PHOTO_COUNT = 4
# Per-photo cap before compression. Matches the URL-import download cap.
MAX_PHOTO_UPLOAD_BYTES = MAX_IMAGE_BYTES
MAX_PHOTO_EDGE_PX = 1600
MAX_PHOTO_PIXELS = 20_000_000
# Re-encoded JPEG sent to the model. Quality steps down if the first pass is bigger.
MAX_PHOTO_SENT_BYTES = 1_500_000

# Same JSON keys as PROMPT_TEMPLATE / parse_recipe_dict. {photo_count} and
# {photo_noun} describe the attachment; {allowed_categories} is the user's list.
PHOTO_PROMPT_TEMPLATE = """You are a data normalizer for a recipe app. The attached {photo_count} {photo_noun} show ONE recipe card or cookbook page, in order. Convert ONLY what is visible into the app's JSON format. Do not invent, add, or omit ingredients or steps. If a word is unclear, transcribe the best reading of the marks on the page and do not fill gaps from general knowledge. If the pages disagree, prefer the later page when it is clearly a correction.

Return ONLY valid JSON with this exact structure:
{{
  "recipe_name": "<the recipe's name as written>",
  "description": "<1-2 sentence description, from the page if available>",
  "recipe_category": "<one of: {allowed_categories}>",
  "meal_type": "<one of: appetizer|breakfast|lunch|dinner|dessert|side|snack|sauce|other>",
  "diet_pref": "<one of: none|vegetarian|vegan|gluten-free|dairy-free|keto|paleo>",
  "prep_time": <integer minutes or null>,
  "cook_time": <integer minutes or null>,
  "difficulty": "<one of: Easy|Medium|Hard>",
  "servings": <integer or null>,
  "ingredients": [
    {{"ingredient_name": "Ingredient Name", "ingredient_category": "<category>", "quantity": <float or null>, "unit": "<unit or null>"}}
  ],
  "directions": "<Step one.\\nStep two.\\nStep three.>",
  "notes": "<optional tips from the page, or null>"
}}

Rules:
- Include EVERY ingredient that is visible, names in Title Case, preparation hints (e.g. "sifted", "chopped") dropped from the name
- Split each ingredient line into quantity (float, e.g. 0.5), unit, and name; if an amount has no clean unit match, pick the closest allowed unit or null
- ingredient_category must be one of: produce|dairy|deli|meat|condiments|oils-and-vinegars|seafood|pantry|spices|frozen|bakery|baking|beverages|other
- unit must be one of: tbs|tsp|cup|oz|lbs|stick|bag|box|can|jar|package|piece|slice|whole|pinch|dash|to-taste
- Keep every direction step that is visible, separated by \\n (no step numbers)
- If only a total time is given, put it in cook_time and leave prep_time null
- diet_pref: use "none" unless the recipe is clearly dietary
- difficulty: estimate from the number of steps and techniques
- If the photos contain NO recipe at all, return exactly: {{"no_recipe_found": true}}"""
