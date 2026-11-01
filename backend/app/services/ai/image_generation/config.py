"""Configuration for the Image Generation AI service."""

from app.services.ai.config import FALLBACK_GEMINI_IMAGE_MODEL, GEMINI_IMAGE_MODEL

# Model settings
MODEL_NAME = GEMINI_IMAGE_MODEL
FALLBACK_MODEL_NAME = FALLBACK_GEMINI_IMAGE_MODEL

# Aspect ratios
ASPECT_RATIO = "1:1"  # Square format for reference/thumbnail images
BANNER_ASPECT_RATIO = "21:9"  # Ultrawide format for banner images (Gemini's widest)

# Output resolution (valid: "512", "1K", "2K", "4K")
REFERENCE_IMAGE_SIZE = "1K"
BANNER_IMAGE_SIZE = "1K"

# Environment variable for API key
API_KEY_ENV_VAR = "GEMINI_IMAGE_API_KEY"

# Default prompt template for square food photography (reference images)
PROMPT_TEMPLATE = (
    "A professional cookbook-quality food photograph of {recipe_name}. "
    "Style the scene — surface, props, lighting, and camera angle — "
    "to match the character of this specific dish. "
    "Vary the composition naturally: choose whichever angle, surface, "
    "and props a professional food stylist would select for this recipe. "
    "Shallow depth of field, natural light, appetizing presentation, "
    "high detail, no people, no hands, no text, square format."
)

# Prompt template for wide banner images (standalone generation, no reference)
BANNER_PROMPT_TEMPLATE = (
    "A professional cookbook-quality food photograph of {recipe_name} "
    "in wide panoramic composition. "
    "Style the scene to match the character of this specific dish. "
    "The dish is the clear focal point, filling the center of the frame. "
    "Shallow depth of field, natural light, appetizing presentation, "
    "high detail, no people, no hands, no text, ultrawide cinematic format."
)

# Prompt template for banner generation using reference image as input
BANNER_FROM_REFERENCE_PROMPT = (
    "Using the provided image as a reference, generate a wide 21:9 panoramic version "
    "of this exact dish ({recipe_name}). Maintain the same food presentation, plating, "
    "garnishes, and lighting. The dish must remain the dominant element, centered and "
    "prominent, occupying the majority of the frame. Extend the scene just enough to "
    "fill the panoramic aspect ratio with subtle context. "
    "No people, no hands, no text, ultrawide cinematic composition."
)
