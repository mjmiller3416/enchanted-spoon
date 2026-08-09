"""app/router.py

Centralised route registration for the Meal Genie API.
"""

from fastapi import APIRouter

from app.api import (
    admin,
    categories,
    conversion_rules,
    dashboard,
    data_management,
    feedback,
    ingredient_categories,
    ingredient_units,
    ingredients,
    meals,
    planner,
    recipe_groups,
    recipes,
    settings,
    shopping,
    stripe_webhooks,
    upload,
    users,
)
from app.api.ai import (
    assistant_router,
    cooking_tips_router,
    image_generation_router,
    meal_suggestions_router,
    nutrition_estimation_router,
    recipe_generation_router,
    recipe_import_router,
)

api_router = APIRouter()

# ── Core domain routes ───────────────────────────────────────────────────
api_router.include_router(recipes.router, prefix="/api/recipes", tags=["recipes"])
api_router.include_router(recipe_groups.router, prefix="/api/recipe-groups", tags=["recipe-groups"])
api_router.include_router(categories.router, prefix="/api/categories", tags=["categories"])
api_router.include_router(meals.router, prefix="/api/meals", tags=["meals"])
api_router.include_router(planner.router, prefix="/api/planner", tags=["planner"])
api_router.include_router(shopping.router, prefix="/api/shopping", tags=["shopping"])
api_router.include_router(ingredients.router, prefix="/api/ingredients", tags=["ingredients"])
api_router.include_router(ingredient_categories.router, prefix="/api/ingredient-categories", tags=["ingredient-categories"])
api_router.include_router(ingredient_units.router, prefix="/api/ingredient-units", tags=["ingredient-units"])

# ── Supporting routes ────────────────────────────────────────────────────
api_router.include_router(data_management.router, prefix="/api/data-management", tags=["data-management"])
api_router.include_router(upload.router, prefix="/api/upload", tags=["upload"])
api_router.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
api_router.include_router(conversion_rules.router, prefix="/api/unit-conversions", tags=["unit-conversions"])
api_router.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
api_router.include_router(settings.router, prefix="/api/settings", tags=["settings"])
api_router.include_router(users.router, prefix="/api/users", tags=["users"])

# ── Admin routes ─────────────────────────────────────────────────────────
api_router.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# ── Webhooks (unauthenticated, verified via provider signature) ─────────
api_router.include_router(stripe_webhooks.router, prefix="/api/webhooks/stripe", tags=["webhooks"])

# ── AI-powered routes ────────────────────────────────────────────────────
api_router.include_router(cooking_tips_router, prefix="/api/ai/cooking-tip", tags=["ai", "cooking-tips"])
# TODO: rename URL prefix to /api/ai/assistant (requires frontend changes)
api_router.include_router(assistant_router, prefix="/api/ai/meal-genie", tags=["ai", "meal-genie"])
api_router.include_router(image_generation_router, prefix="/api/ai/image-generation", tags=["ai", "image-generation"])
api_router.include_router(meal_suggestions_router, prefix="/api/ai/meal-suggestions", tags=["ai", "meal-suggestions"])
api_router.include_router(nutrition_estimation_router, prefix="/api/ai/nutrition-estimation", tags=["ai", "nutrition-estimation"])
# TODO: rename URL prefix to /api/ai/recipe-generation (requires frontend changes)
api_router.include_router(recipe_generation_router, prefix="/api/ai/wizard-generation", tags=["ai", "recipe-generation"])
api_router.include_router(recipe_import_router, prefix="/api/ai/recipe-import", tags=["ai", "recipe-import"])
