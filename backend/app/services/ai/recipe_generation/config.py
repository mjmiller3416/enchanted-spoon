"""Configuration for the Recipe Generation AI service."""

from app.services.ai.config import GEMINI_RECIPE_MODEL

# Model settings
MODEL_NAME = GEMINI_RECIPE_MODEL
TEMPERATURE = 0.7  # Balanced creativity + consistency
MAX_OUTPUT_TOKENS = 8192  # Extra headroom for thinking tokens + full recipe JSON

# Environment variable for API key (reuses the assistant key)
API_KEY_ENV_VAR = "GEMINI_RECIPE_GENERATION_API_KEY"

# Default categories used when no user categories are provided
DEFAULT_CATEGORIES = [
    "american", "chinese", "french", "indian", "italian",
    "japanese", "mediterranean", "mexican", "thai", "other",
]

# Prompt template for generating a complete recipe from a user description.
# {allowed_categories} is dynamically interpolated from the user's enabled categories.
PROMPT_TEMPLATE = """You are a professional recipe developer. Generate a complete, detailed recipe based on the user's request.

User's request: {prompt}
{preferences_text}

Return ONLY valid JSON with this exact structure:
{{
  "recipe_name": "<creative, descriptive name>",
  "description": "<1-2 sentence appetizing description>",
  "recipe_category": "<one of: {allowed_categories}>",
  "meal_type": "<one of: appetizer|breakfast|lunch|dinner|dessert|side|snack|sauce|other>",
  "diet_pref": "<one of: none|vegetarian|vegan|gluten-free|dairy-free|keto|paleo>",
  "prep_time": <integer minutes>,
  "cook_time": <integer minutes>,
  "difficulty": "<one of: Easy|Medium|Hard>",
  "servings": <integer>,
  "ingredients": [
    {{"ingredient_name": "Ingredient Name", "ingredient_category": "<category>", "quantity": <float>, "unit": "<unit>"}}
  ],
  "directions": "<Step one.\\nStep two.\\nStep three.>",
  "notes": "<optional tips or serving suggestions>"{nutrition_schema}
}}

Rules:
- 6-15 ingredients with names in Title Case
- 5-10 direction steps separated by \\n (no step numbers)
- ingredient_category must be one of: produce|dairy|deli|meat|condiments|oils-and-vinegars|seafood|pantry|spices|frozen|bakery|baking|beverages|other
- unit must be one of: tbs|tsp|cup|oz|lbs|stick|bag|box|can|jar|package|piece|slice|whole|pinch|dash|to-taste
- diet_pref: use "none" unless the recipe is specifically dietary (never null)
- Be realistic with quantities and cooking times
- Base nutrition estimates on standard USDA data if included"""

# Nutrition schema fragment appended when estimate_nutrition=True
NUTRITION_SCHEMA = """,
  "nutrition_facts": {{
    "calories": <integer or null>,
    "protein_g": <float or null>,
    "total_fat_g": <float or null>,
    "saturated_fat_g": <float or null>,
    "trans_fat_g": <float or null>,
    "cholesterol_mg": <float or null>,
    "sodium_mg": <float or null>,
    "total_carbs_g": <float or null>,
    "dietary_fiber_g": <float or null>,
    "total_sugars_g": <float or null>
  }}"""
