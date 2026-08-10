"""API routers for the Whiskful application."""

from .recipes import router as recipes_router
from .planner import router as planner_router
from .shopping import router as shopping_router
from .ingredients import router as ingredients_router

__all__ = [
    "recipes_router",
    "planner_router",
    "shopping_router",
    "ingredients_router",
]
