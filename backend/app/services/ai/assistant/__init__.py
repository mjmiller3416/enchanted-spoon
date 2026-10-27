"""AI assistant service package.

Combines core service and AI generators.
"""

from typing import Optional

from .service import AssistantServiceCore
from .generators import GeneratorsMixin
from .planning import MealPlanningMixin


class AssistantService(MealPlanningMixin, GeneratorsMixin, AssistantServiceCore):
    """Unified AI assistant service combining all functionality.

    Inherits from:
    - AssistantServiceCore: Core chat logic, context building, response processing
    - GeneratorsMixin: AI generation methods (suggestions, recipes, cooking answers)
    - MealPlanningMixin: Planning meals from saved recipes onto the meal planner
    """

    pass


# Singleton pattern
_service_instance: Optional[AssistantService] = None


def get_assistant_service() -> AssistantService:
    """Get the singleton instance of the AI assistant service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AssistantService()
    return _service_instance


__all__ = [
    "AssistantService",
    "get_assistant_service",
]
