"""DTOs for the AI assistant (conversational chat + recipe generation)."""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

from .recipe_generation_dtos import GeneratedIngredientDTO, RecipeGeneratedDTO

# Matches the frontend's MAX_MESSAGES cap in hooks/persistence/useChatHistory.ts
MAX_CONVERSATION_HISTORY = 50


class AssistantMessageDTO(BaseModel):
    """A single message in the conversation."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=8000)


class AssistantRequestDTO(BaseModel):
    """Request DTO for assistant chat."""

    message: str = Field(..., max_length=4000)
    conversation_history: Optional[List[AssistantMessageDTO]] = Field(
        None, max_length=MAX_CONVERSATION_HISTORY
    )


class AssistantResponseDTO(BaseModel):
    """Response DTO for assistant chat.

    Can include recipe data if the AI decides to generate a recipe.
    """

    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    # Optional recipe data (if AI generated one)
    recipe: Optional[RecipeGeneratedDTO] = None
    reference_image_data: Optional[str] = None  # Base64 encoded (1:1 square)
    banner_image_data: Optional[str] = None  # Base64 encoded (21:9 ultrawide)


class AssistantRecipeRequestDTO(BaseModel):
    """Request DTO for generating a recipe via the assistant (legacy endpoint)."""

    message: str = Field(..., max_length=4000)
    conversation_history: Optional[List[AssistantMessageDTO]] = Field(
        None, max_length=MAX_CONVERSATION_HISTORY
    )
    generate_image: bool = True


class AssistantRecipeResponseDTO(BaseModel):
    """Response DTO containing generated recipe + optional images (legacy endpoint)."""

    success: bool
    recipe: Optional[RecipeGeneratedDTO] = None
    reference_image_data: Optional[str] = None  # Base64 encoded (1:1 square)
    banner_image_data: Optional[str] = None  # Base64 encoded (21:9 ultrawide)
    ai_message: Optional[str] = None  # Friendly message from AI
    needs_more_info: bool = False  # True if AI is asking follow-up questions
    error: Optional[str] = None
