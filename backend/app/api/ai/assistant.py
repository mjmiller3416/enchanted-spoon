"""API router for AI assistant (conversational chat + recipe generation)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_within_usage_limit
from app.database.db import get_session
from app.dtos.assistant_dtos import (
    AssistantRequestDTO,
    AssistantResponseDTO,
    AssistantRecipeRequestDTO,
    AssistantRecipeResponseDTO,
)
from app.services.ai.assistant import get_assistant_service
from app.services.ai.assistant.context import (
    should_include_ingredients,
    should_include_shopping_list,
)
from app.services.ai.optional_images import generate_optional_recipe_images
from app.services.ai.user_context_builder import UserContextBuilder
from app.services.planner import PlannerService
from app.services.shopping import ShoppingService
from app.models.user import User
from app.services.usage_service import UsageService
from app.api.errors import internal_error

router = APIRouter()


@router.post("/chat", response_model=AssistantResponseDTO)
async def chat_with_assistant(
    request: AssistantRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_assistant_messages")),
) -> AssistantResponseDTO:
    """Unified chat endpoint for the AI assistant.

    The AI decides what action to take:
    - Suggest recipes
    - Generate a full recipe
    - Answer a cooking question
    - Add items to the shopping list
    - Plan meals from saved recipes onto the meal planner

    Uses Gemini function calling to intelligently route requests.
    """
    shopping_service = ShoppingService(session, current_user.id)
    planner_service = PlannerService(session, current_user.id)
    try:
        # Convert history to dict format for keyword detection
        history_dicts = None
        if request.conversation_history:
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in request.conversation_history
            ]

        # Determine what context to load based on message content
        include_ingredients = should_include_ingredients(request.message, history_dicts)
        include_shopping = should_include_shopping_list(request.message, history_dicts)

        # Build context data
        context_builder = UserContextBuilder(session, current_user.id)
        context_data = context_builder.build_context_data(
            include_ingredients=include_ingredients,
            include_shopping_list=include_shopping,
        )

        # Call the service
        service = get_assistant_service()
        result = await service.chat(
            message=request.message,
            conversation_history=request.conversation_history,
            user_context_data=context_data,
            add_shopping_items=shopping_service.add_manual_items,
            load_recipe_catalog=context_builder.build_recipe_catalog,
            add_planner_meals=planner_service.add_new_meals_to_planner,
        )

        if result.get("type") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))

        # Handle recipe generation with images
        recipe = result.get("recipe")
        reference_image_data = None
        banner_image_data = None

        # Chat creates recipe text only. Photos are an explicit recipe action.

        # Track usage (silent fail - don't break AI feature for tracking issues)
        try:
            # The assistant message itself was counted by require_within_usage_limit
            usage_service = UsageService(session, current_user.id)
            # Track recipe creation if a recipe was generated
            if recipe:
                usage_service.increment("recipes_created")
        except Exception:
            pass

        return AssistantResponseDTO(
            success=True,
            response=result.get("response"),
            recipe=recipe,
            reference_image_data=reference_image_data,
            banner_image_data=banner_image_data,
            shopping_update=result.get("shopping_update"),
            planner_update=result.get("planner_update"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error("Assistant error. Please try again.")


# Keep /ask as backwards-compatible alias that routes to /chat
@router.post("/ask", response_model=AssistantResponseDTO)
async def ask_assistant(
    request: AssistantRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_assistant_messages")),
) -> AssistantResponseDTO:
    """Send a message to the AI assistant and get a response.

    This endpoint is an alias for /chat for backwards compatibility.
    The AI may decide to generate a recipe if the user asks for one.
    """
    return await chat_with_assistant(request, session, current_user)


@router.post("/generate-recipe", response_model=AssistantRecipeResponseDTO)
async def generate_recipe(
    request: AssistantRecipeRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_within_usage_limit("ai_assistant_messages")),
) -> AssistantRecipeResponseDTO:
    """Generate a complete recipe with optional AI image.

    This endpoint is kept for backwards compatibility.
    Consider using /chat instead, which handles recipe generation automatically.
    """
    try:
        # Convert history to dict format for keyword detection
        history_dicts = None
        if request.conversation_history:
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in request.conversation_history
            ]

        # Determine what context to load
        include_ingredients = should_include_ingredients(request.message, history_dicts)
        include_shopping = should_include_shopping_list(request.message, history_dicts)

        # Build context
        context_builder = UserContextBuilder(session, current_user.id)
        context_data = context_builder.build_context_data(
            include_ingredients=include_ingredients,
            include_shopping_list=include_shopping,
        )

        # Call service
        service = get_assistant_service()
        result = await service.chat(
            message=request.message,
            conversation_history=request.conversation_history,
            user_context_data=context_data,
        )

        if result.get("type") == "error":
            # Failure reported in the body rather than raised: refund by hand
            try:
                UsageService(session, current_user.id).release("ai_assistant_messages")
            except Exception:
                pass
            return AssistantRecipeResponseDTO(
                success=False,
                error=result.get("error", "Failed to generate recipe"),
            )

        # Check if we got a recipe
        recipe = result.get("recipe")
        if not recipe:
            # No recipe generated - AI is probably asking for more info
            return AssistantRecipeResponseDTO(
                success=True,
                ai_message=result.get("response"),
                needs_more_info=True,
            )

        # We have a recipe - generate images if requested
        reference_image_data = None
        banner_image_data = None

        if request.generate_image and recipe:
            reference_image_data, banner_image_data = await generate_optional_recipe_images(
                session, current_user, recipe.recipe_name
            )

        # Track usage (silent fail - don't break AI feature for tracking issues)
        try:
            # The assistant message itself was counted by require_within_usage_limit
            usage_service = UsageService(session, current_user.id)
            # Track recipe creation if a recipe was generated
            if recipe:
                usage_service.increment("recipes_created")
        except Exception:
            pass

        return AssistantRecipeResponseDTO(
            success=True,
            recipe=recipe,
            reference_image_data=reference_image_data,
            banner_image_data=banner_image_data,
            ai_message=result.get("response"),
            needs_more_info=False,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise internal_error()
    except Exception as e:
        raise internal_error("Recipe generation error. Please try again.")
