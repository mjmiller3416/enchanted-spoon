"""app/dtos/sample_data_dtos.py

Pydantic DTOs for starter-pack (sample) content.
"""

from pydantic import BaseModel, ConfigDict


class SampleDataStatusDTO(BaseModel):
    """Whether the user still has untouched starter content."""

    model_config = ConfigDict(from_attributes=True)

    has_sample_data: bool
    recipe_count: int
    meal_count: int


class SampleDataSeedResultDTO(BaseModel):
    """What seeding the starter pack created."""

    recipes_created: int
    meals_created: int
    planner_entries_created: int


class SampleDataRemovalResultDTO(BaseModel):
    """What removing starter content deleted (and kept)."""

    recipes_removed: int
    meals_removed: int
    # Sample recipes kept because one of the user's own meals uses them
    recipes_kept: int
