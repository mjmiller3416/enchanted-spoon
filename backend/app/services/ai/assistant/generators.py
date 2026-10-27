"""app/services/ai/assistant/generators.py

AI content generation methods for the assistant.
Handles recipe suggestions, full recipe generation, and cooking question answers.
"""

import logging
from typing import List, Optional

from app.dtos.recipe_generation_dtos import (
    RecipeGeneratedDTO,
    RecipeGenerationPreferencesDTO,
    RecipeGenerationRequestDTO,
)
from app.dtos.shopping_dtos import ManualItemCreateDTO
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.recipe_generation import get_recipe_generation_service
from app.services.ai.recipe_generation.service import (
    RecipeGenerationError,
    RecipeParseError,
)
from app.services.ai.response_utils import extract_text_from_response

from .prompts import MODEL_NAME, API_KEY_ENV_VAR
from .service import PlannerMealAdder, RecipeCatalogLoader, ShoppingItemAdder
from .tools import SHOPPING_CATEGORIES, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


class GeneratorsMixin:
    """Mixin providing AI generation methods for the assistant."""

    async def _handle_function_call(
        self,
        tool_name: str,
        args: dict,
        context_data: Optional[dict],
        contents: list,
        model_turn=None,
        add_shopping_items: Optional[ShoppingItemAdder] = None,
        *,
        load_recipe_catalog: Optional[RecipeCatalogLoader] = None,
        add_planner_meals: Optional[PlannerMealAdder] = None,
    ) -> dict:
        """Execute a function call and return appropriate response."""

        if tool_name == "suggest_recipes":
            # Immediate Generation Loop: The function call tells us the user wants
            # suggestions, but we need to generate the actual text response.
            return self._generate_suggestions_response(
                args, context_data, contents, model_turn
            )

        elif tool_name == "create_recipe":
            # Generate a full recipe with structured JSON
            recipe = await self._generate_recipe_from_args(args, context_data)
            if recipe is None:
                # Generation failed or came back hollow (no ingredients) — tell the
                # user instead of silently handing them an empty recipe draft.
                return {
                    "type": "chat",
                    "response": (
                        f"Hmm, I had trouble putting together a full recipe for "
                        f"{args.get('recipe_name', 'that')} — mind asking again, "
                        f"maybe with a bit more detail?"
                    ),
                    "tool_args": args,
                }
            return {
                "type": "recipe",
                "response": f"Here's your {args.get('recipe_name', 'recipe')}! 🎉",
                "recipe": recipe,
                "tool_args": args,
            }

        elif tool_name == "answer_cooking_question":
            # For cooking questions, we use a follow-up call to get a proper response
            return self._generate_cooking_answer(args, contents, model_turn)

        elif tool_name == "add_to_shopping_list":
            return self._add_items_to_shopping_list(
                args, contents, model_turn, add_shopping_items
            )

        elif tool_name == "add_meals_to_planner":
            # Implemented by MealPlanningMixin
            return self._add_meals_to_planner(
                args,
                context_data,
                contents,
                model_turn,
                load_recipe_catalog,
                add_planner_meals,
            )

        # Fallback
        return {"type": "chat", "response": None}

    def _finalize_after_tool_call(
        self,
        contents: list,
        model_turn,
        tool_name: str,
        instruction: str,
        fallback: str,
        result: Optional[dict] = None,
    ) -> str:
        """Continue a Gemini function-calling turn to produce the final text.

        Gemini 3.x requires the model's original ``function_call`` part (which
        carries a ``thought_signature``) to be replayed, immediately followed by
        a matching ``function_response`` part, with the tool declarations still
        present in the request. We then ask the model to finalize its answer with
        ``mode: NONE`` so it returns natural-language text instead of attempting
        another tool call.

        The previous implementation appended a *fresh user text prompt* without
        the function_call/function_response pair. Under Gemini 3.x that returns
        ``finish_reason=MALFORMED_FUNCTION_CALL`` with no content, which silently
        collapsed to the canned ``fallback`` string — the assistant appeared to
        "do nothing" with no backend error.

        Args:
            contents: The conversation contents sent on the initial tool call.
            model_turn: The model's response Content holding the function_call
                part (with its thought_signature). May be ``None`` in tests.
            tool_name: Name of the tool that was called.
            instruction: Natural-language instruction describing the text to
                generate (carried in the function_response payload).
            fallback: Text to return if the model yields no usable text.
            result: Optional tool outcome merged into the function_response so
                the model confirms what actually happened (overrides ``status``).

        Returns:
            The generated text, or ``fallback`` if none was produced.
        """
        client = get_gemini_client(API_KEY_ENV_VAR)

        follow_contents = list(contents)
        if model_turn is not None:
            follow_contents.append(model_turn)
            follow_contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": tool_name,
                                "response": {
                                    "status": "ok",
                                    "instruction": instruction,
                                    **(result or {}),
                                },
                            }
                        }
                    ],
                }
            )
        else:
            # Defensive path (e.g. unit tests with no real model turn).
            follow_contents.append(
                {"role": "user", "parts": [{"text": instruction}]}
            )

        gen_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=follow_contents,
            config={
                "tools": [{"function_declarations": TOOL_DEFINITIONS}],
                "tool_config": {"function_calling_config": {"mode": "NONE"}},
                "temperature": 0.8,
            },
        )

        return extract_text_from_response(gen_response) or fallback

    def _generate_suggestions_response(
        self,
        args: dict,
        context_data: Optional[dict],
        contents: list,
        model_turn=None,
    ) -> dict:
        """Generate recipe suggestions text based on tool arguments."""
        # Build a prompt that includes context about what the user wants
        context_parts = []
        if args.get("main_ingredient"):
            context_parts.append(f"Main ingredient: {args['main_ingredient']}")
        if args.get("cuisine_style"):
            context_parts.append(f"Style: {args['cuisine_style']}")
        if args.get("dietary_restrictions"):
            context_parts.append(f"Dietary: {args['dietary_restrictions']}")
        if args.get("time_constraint"):
            context_parts.append(f"Time: {args['time_constraint']}")
        if args.get("mood_or_vibe"):
            context_parts.append(f"Vibe: {args['mood_or_vibe']}")

        context_str = ", ".join(context_parts) if context_parts else "general dinner ideas"

        # Check for saved recipes to reference
        saved_recipes_mention = ""
        if context_data and context_data.get("saved_recipes"):
            saved_recipes_mention = "\nRemember to check her saved recipes first and mention any relevant matches!"

        prompt = f"""Based on the user's request ({context_str}), suggest 4-6 creative recipe ideas.
{saved_recipes_mention}

Follow the 'RECIPE SUGGESTIONS' format from your system instructions:
- **Bold Recipe Name**
- 1-2 sentence description (menu teaser style, not instructions)
- Blank line between each
- End with: "Want me to turn any of these into a full recipe? Just say which one! 🍳"

Be warm, enthusiastic, and use 2-4 emojis naturally placed."""

        # Continue the tool conversation to generate the suggestions text.
        final_text = self._finalize_after_tool_call(
            contents,
            model_turn,
            "suggest_recipes",
            prompt,
            "Here are some ideas! 🍳",
        )

        return {
            "type": "suggestions",
            "response": final_text,
            "tool_args": args,
        }

    def _generate_cooking_answer(
        self, args: dict, contents: list, model_turn=None
    ) -> dict:
        """Generate a cooking question answer."""
        question_type = args.get("question_type", "general")
        context = args.get("context", "")

        prompt = f"""Answer this {question_type} cooking question. Context: {context}

Be warm and helpful. Start with the most direct answer, then add one pro tip.
Keep it concise (2-4 sentences unless it needs more detail).
Use your friendly Genie personality."""

        final_text = self._finalize_after_tool_call(
            contents,
            model_turn,
            "answer_cooking_question",
            prompt,
            "Let me help with that!",
        )

        return {
            "type": "chat",
            "response": final_text,
            "tool_args": args,
        }

    def _add_items_to_shopping_list(
        self,
        args: dict,
        contents: list,
        model_turn=None,
        add_shopping_items: Optional[ShoppingItemAdder] = None,
    ) -> dict:
        """Write the requested items to the shopping list, then confirm the outcome.

        The write happens before the follow-up model call so Genie's reply is
        based on what actually landed (added / moved back / already listed)
        rather than on what it intended to do.
        """
        items = self._parse_shopping_items(args.get("items"))
        if not items:
            return {
                "type": "chat",
                "response": "Happy to add things to your list — what should I put on it? 🛒",
                "tool_args": args,
            }

        result = add_shopping_items(items) if add_shopping_items else None
        if result is None:
            # Canned on purpose: a model-written reply here risks claiming success
            return {
                "type": "chat",
                "response": (
                    "Hmm, I couldn't update your shopping list just now — "
                    "mind trying again in a sec?"
                ),
                "tool_args": args,
            }

        summary = {
            "added": [i.ingredient_name for i in result.added],
            "moved_back_to_need": [i.ingredient_name for i in result.reactivated],
            "already_on_list": result.already_listed,
        }
        instruction = (
            "Confirm the shopping list update in 1-2 short sentences. 'added' items "
            "were newly added; 'moved_back_to_need' items were checked off and are "
            "needed again (just say they're added); 'already_on_list' items were "
            "skipped because they're already on the list. Only mention items from "
            "these lists. Use 1-2 emojis."
        )
        final_text = self._finalize_after_tool_call(
            contents,
            model_turn,
            "add_to_shopping_list",
            instruction,
            self._describe_shopping_update(summary),
            result=summary,
        )

        return {
            "type": "shopping",
            "response": final_text,
            "shopping_update": result,
            "tool_args": args,
        }

    @staticmethod
    def _parse_shopping_items(raw_items) -> List[ManualItemCreateDTO]:
        """Convert the tool's item list into validated DTOs, dropping bad or repeat entries."""
        items: List[ManualItemCreateDTO] = []
        seen: set[str] = set()
        for raw in raw_items or []:
            try:
                raw = dict(raw)
                category = str(raw.get("category") or "").strip().lower()
                dto = ManualItemCreateDTO(
                    ingredient_name=raw.get("name") or "",
                    quantity=raw.get("quantity") or 1,
                    unit=raw.get("unit") or None,
                    category=category if category in SHOPPING_CATEGORIES else "other",
                )
            except (TypeError, ValueError) as e:  # pydantic ValidationError is a ValueError
                logger.warning(f"[Assistant] Skipping invalid shopping item {raw!r}: {e}")
                continue
            key = dto.ingredient_name.lower()
            if key not in seen:
                seen.add(key)
                items.append(dto)
        return items

    @staticmethod
    def _describe_shopping_update(summary: dict) -> str:
        """Plain confirmation used when the model returns no follow-up text."""

        def join(names: List[str]) -> str:
            return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"

        added = summary["added"] + summary["moved_back_to_need"]
        listed = summary["already_on_list"]
        parts = []
        if added:
            parts.append(f"Added {join(added)} to your shopping list! 🛒")
        if listed:
            verb = "is" if len(listed) == 1 else "are"
            parts.append(f"{join(listed)} {verb} already on there.")
        return " ".join(parts)

    async def _generate_recipe_from_args(
        self, args: dict, context_data: Optional[dict] = None
    ) -> Optional[RecipeGeneratedDTO]:
        """Generate a structured recipe by delegating to the recipe generation service.

        Bridges the assistant's tool-call arguments to the shared recipe
        generation service, which uses the same prompt template and parsing
        logic as the prompt-based generation flow.
        """
        recipe_name = args.get("recipe_name", "Untitled Recipe")
        style_notes = args.get("style_notes", "")
        dietary = args.get("dietary_restrictions", "")
        servings = args.get("servings", 4)

        # Build a natural-language prompt from the tool arguments
        prompt_parts = [f"Generate a complete recipe for: {recipe_name}"]
        if style_notes:
            prompt_parts.append(f"Style notes: {style_notes}")
        if dietary and dietary != "none":
            prompt_parts.append(f"Dietary restrictions: {dietary}")

        # Use user's enabled categories from context, falling back to service defaults
        allowed_categories = (
            context_data.get("allowed_categories", []) if context_data else []
        )

        request = RecipeGenerationRequestDTO(
            prompt="\n".join(prompt_parts),
            allowed_categories=allowed_categories,
            preferences=None,
            generate_image=False,
            estimate_nutrition=False,
        )
        # Override servings in the prompt via preferences if non-default
        if servings and servings != 4:
            request.preferences = RecipeGenerationPreferencesDTO(servings=servings)

        service = get_recipe_generation_service()

        # A single malformed/truncated AI response (e.g. a longer, more elaborate
        # recipe hitting the output token limit or emitting one bad ingredient
        # entry) shouldn't sink the whole request — retry a couple of times
        # before telling the user generation failed.
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                result = await service.generate(request)
                if result.success and result.recipe and result.recipe.ingredients:
                    return result.recipe
                logger.warning(
                    f"[Assistant] Recipe generation for '{recipe_name}' produced no "
                    f"usable recipe (attempt {attempt}/{max_attempts}, "
                    f"success={result.success}, ingredients="
                    f"{len(result.recipe.ingredients) if result.recipe else 0})"
                )
            except (RecipeParseError, RecipeGenerationError) as e:
                logger.warning(
                    f"[Assistant] Recipe generation via service failed "
                    f"(attempt {attempt}/{max_attempts}): {e}"
                )
            except Exception as e:
                logger.warning(f"[Assistant] Recipe generation via service failed: {e}")
                break

        # Let the caller know generation failed instead of handing back a
        # recipe that looks complete but has no ingredients/directions.
        return None
