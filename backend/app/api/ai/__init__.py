"""AI API routers."""

from .cooking_tips import router as cooking_tips_router
from .assistant import router as assistant_router
from .image_generation import router as image_generation_router
from .meal_suggestions import router as meal_suggestions_router
from .nutrition_estimation import router as nutrition_estimation_router
from .recipe_generation import router as recipe_generation_router
from .recipe_import import router as recipe_import_router
from .photo_import import router as photo_import_router

__all__ = [
    "cooking_tips_router",
    "assistant_router",
    "image_generation_router",
    "meal_suggestions_router",
    "nutrition_estimation_router",
    "recipe_generation_router",
    "recipe_import_router",
    "photo_import_router",
]
