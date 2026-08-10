"""app/services/ai/assistant/service.py

Core AI assistant service logic.
Handles chat interface, context building, and response processing.
"""

from typing import Optional, List

from app.dtos.assistant_dtos import AssistantMessageDTO
from app.services.ai.gemini_client import get_gemini_client

from .prompts import MODEL_NAME, API_KEY_ENV_VAR, get_full_system_prompt
from .tools import TOOL_DEFINITIONS
from .context import (
    build_user_context_prompt,
    should_include_ingredients,
    should_include_shopping_list,
)


class AssistantServiceCore:
    """Core AI assistant service with chat interface and response processing."""

    def __init__(self) -> None:
        """Initialize the AI assistant service."""
        # Validate eagerly so we fail fast if misconfigured
        get_gemini_client(API_KEY_ENV_VAR)

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[AssistantMessageDTO]] = None,
        user_context_data: Optional[dict] = None,
    ) -> dict:
        """Main entry point for all assistant interactions.

        The AI decides what action to take based on the message:
        - Suggest recipes
        - Generate a full recipe
        - Answer a cooking question

        Args:
            message: The user's message.
            conversation_history: Optional list of previous messages.
            user_context_data: Dict with saved_recipes, meal_plan, etc.

        Returns:
            dict with 'type' (chat|suggestions|recipe|error), 'response', and
            optionally 'recipe' or 'tool_args'.
        """
        try:
            client = get_gemini_client(API_KEY_ENV_VAR)

            # Build context based on message content
            user_context = self._build_context(
                message, conversation_history, user_context_data
            )
            system_prompt = get_full_system_prompt(user_context)

            # Build conversation contents
            contents = self._build_contents(system_prompt, conversation_history, message)

            # Call Gemini with function calling
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config={
                    "tools": [{"function_declarations": TOOL_DEFINITIONS}],
                    "tool_config": {"function_calling_config": {"mode": "AUTO"}},
                    "temperature": 0.8,
                },
            )

            # Process the response
            return await self._process_response(response, user_context_data, contents)

        except Exception as e:
            return {
                "type": "error",
                "response": None,
                "error": str(e),
            }

    def _build_context(
        self,
        message: str,
        history: Optional[List[AssistantMessageDTO]],
        context_data: Optional[dict],
    ) -> str:
        """Build user context string based on message needs."""
        if not context_data:
            return ""

        saved_recipes = context_data.get("saved_recipes", [])
        meal_plan = context_data.get("meal_plan", [])
        recipe_ingredients = None
        shopping_list = None

        # Convert history to dict format for keyword detection
        history_dicts = None
        if history:
            history_dicts = [{"role": m.role, "content": m.content} for m in history]

        # Conditionally load ingredients
        if should_include_ingredients(message, history_dicts):
            recipe_ingredients = context_data.get("recipe_ingredients", {})

        # Conditionally load shopping list
        if should_include_shopping_list(message, history_dicts):
            shopping_list = context_data.get("shopping_list", {})

        return build_user_context_prompt(
            saved_recipes=saved_recipes,
            meal_plan=meal_plan,
            shopping_list=shopping_list,
            recipe_ingredients=recipe_ingredients,
        )

    def _build_contents(
        self,
        system_prompt: str,
        history: Optional[List[AssistantMessageDTO]],
        message: str,
    ) -> list:
        """Build the conversation contents for Gemini."""
        contents = []

        # System prompt as initial user message + model acknowledgment
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append(
            {
                "role": "model",
                "parts": [
                    {"text": "Got it! I'm Genie, ready to help. What sounds good tonight? 🍳"}
                ],
            }
        )

        # Add conversation history
        if history:
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        # Add the current message
        contents.append({"role": "user", "parts": [{"text": message}]})

        return contents

    async def _process_response(
        self, response, user_context_data: Optional[dict], contents: list
    ) -> dict:
        """Process Gemini response, handling function calls."""
        if not response or not response.candidates:
            return {"type": "error", "response": None, "error": "No response from AI"}

        # Gemini 3.x may emit a conversational preamble text part *before* the
        # function_call part (e.g. "Here are some ideas! 🔍"). We must scan all
        # parts and prioritize the function call over any preamble text —
        # otherwise we'd return the preamble as a plain chat reply and never
        # execute the tool, dropping the suggestions/recipe entirely.
        function_call = None
        model_turn = None
        text_response = None

        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue

            for part in candidate.content.parts:
                if hasattr(part, "thought") and part.thought:
                    continue

                # Capture the first function call we encounter.
                if (
                    function_call is None
                    and hasattr(part, "function_call")
                    and part.function_call
                ):
                    function_call = part.function_call
                    # Preserve the model's turn verbatim — Gemini 3.x attaches a
                    # thought_signature to the function_call part that MUST be
                    # replayed when continuing the tool conversation, otherwise
                    # the follow-up call fails with MALFORMED_FUNCTION_CALL.
                    model_turn = candidate.content
                    continue

                # Capture the first non-empty text part as a fallback.
                if (
                    text_response is None
                    and hasattr(part, "text")
                    and part.text
                    and part.text.strip()
                ):
                    text_response = part.text.strip()

        # A tool call always takes precedence over preamble text.
        if function_call is not None:
            return await self._handle_function_call(
                function_call.name,
                dict(function_call.args) if function_call.args else {},
                user_context_data,
                contents,
                model_turn,
            )

        # No tool call — this was a plain conversational reply.
        if text_response is not None:
            return {
                "type": "chat",
                "response": text_response,
            }

        return {"type": "error", "response": None, "error": "Could not parse response"}

    async def _handle_function_call(
        self,
        tool_name: str,
        args: dict,
        context_data: Optional[dict],
        contents: list,
        model_turn=None,
    ) -> dict:
        """Execute a function call and return appropriate response.

        This method is implemented by the GeneratorsMixin.
        Subclasses should override this to provide actual implementation.
        """
        raise NotImplementedError("_handle_function_call must be implemented by subclass")
