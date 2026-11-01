"""app/services/ai/config.py

Model defaults. Environment variables override these when set; this change
does not write Railway variables.

Lite calls: cooking tips, meal suggestions, nutrition, recipe import.
Recipe generation uses the recipe model. The assistant stays on 3.6 Flash.
Image default is the lite image model, with a flash-image fallback in the
image service.
"""

import os

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
DEFAULT_GEMINI_ASSISTANT_MODEL = "gemini-3.6-flash"
DEFAULT_GEMINI_LITE_MODEL = "gemini-3.1-flash-lite"
DEFAULT_GEMINI_RECIPE_MODEL = "gemini-3.5-flash-lite"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-3.1-flash-lite-image"
FALLBACK_GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
GEMINI_ASSISTANT_MODEL = os.getenv("GEMINI_ASSISTANT_MODEL", DEFAULT_GEMINI_ASSISTANT_MODEL)
GEMINI_LITE_MODEL = os.getenv("GEMINI_LITE_MODEL", DEFAULT_GEMINI_LITE_MODEL)
GEMINI_RECIPE_MODEL = os.getenv("GEMINI_RECIPE_MODEL", DEFAULT_GEMINI_RECIPE_MODEL)
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", DEFAULT_GEMINI_IMAGE_MODEL)

# Gemini 3.x calls omit temperature. The parameter is still accepted by the
# SDK, and the Gemini 3 docs warn that values other than the default 1.0 can
# loop or degrade output. Lite and recipe models follow the same rule.
MINIMAL_THINKING: dict = {"thinking_level": "minimal"}
ASSISTANT_MAX_OUTPUT_TOKENS = 1024
PLANNING_MAX_OUTPUT_TOKENS = 2048
