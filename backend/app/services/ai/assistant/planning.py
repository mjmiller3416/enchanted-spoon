"""app/services/ai/assistant/planning.py

Meal planning for the assistant. Turns a request like "4 dinners, 3 with ground
beef, 1 chicken, 1-2 sides each" into meals built from the user's saved recipes
and adds them to the meal planner.
"""

import json
import logging
import random
from typing import List, Optional

from app.dtos.meal_dtos import MealCreateDTO
from app.repositories.planner import MAX_PLANNER_ENTRIES
from app.services.ai.gemini_client import get_gemini_client
from app.services.ai.parse_utils import safe_int
from app.services.ai.response_utils import extract_text_from_response

from .prompts import API_KEY_ENV_VAR, MODEL_NAME
from .service import PlannerMealAdder, RecipeCatalogLoader

logger = logging.getLogger(__name__)

# Mirrors MealServiceCore.MAX_SIDE_RECIPES (MealCreateDTO rejects more)
MAX_SIDES_PER_MEAL = 3

# Some variety between repeat requests, but the picks must follow the rules
PLAN_TEMPERATURE = 0.7

PLANNER_FAILED_REPLY = (
    "Hmm, I couldn't update your meal planner just now — mind trying again in a sec?"
)

# Structured output for the planning call; ids are checked against the library after
MEAL_PLAN_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "meals": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "main_recipe_id": {"type": "INTEGER"},
                    "side_recipe_ids": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                },
                "required": ["main_recipe_id", "side_recipe_ids"],
            },
        },
        "notes": {"type": "STRING"},
    },
    "required": ["meals", "notes"],
}

MEAL_PLAN_PROMPT = """You are planning meals for a home cook's meal planner, using ONLY recipes from her saved library below.

WHAT SHE ASKED FOR:
{requirements}

Plan exactly {meal_count} meal(s).

RULES:
- Every id you return MUST come from the library list. Never invent ids.
- Each meal is one main recipe (main_recipe_id) plus its side dishes (side_recipe_ids).
- Mains: dishes that work as the centerpiece, usually meal_type "dinner" unless she asked for another meal (breakfast, lunch...). Never use the same main twice.
- Sides: prefer meal_type "side" recipes that pair well with the main (cuisine, flavor, balance). At most 3 per meal. Follow her side-dish rule exactly ("1-2 sides" means 1 or 2 for every meal, "no sides" means none). With no rule, add 0-2 sides that fit naturally. Vary sides across meals when the library allows.
- Treat her requirements as rules for the whole plan: counts ("3 with ground beef") and "at least one" rules span all meals, and one meal can satisfy several (a ground beef pasta counts for both). Judge protein, cuisine (Mexican, Italian...) and dish type (pasta, soup...) from the names and ingredients.
- Lean toward favorites (★) but keep variety. Avoid meals already on her planner unless she asked for them.
- Never swap in a different protein, ingredient or dish for one she explicitly asked for ("lamb" never becomes beef). If no saved recipe fits, leave that meal out, so the plan can have fewer meals or none, and explain the gap in notes.
- Softer preferences (cuisine style, sides, time, variety) can be met as closely as the library allows; mention any compromise in notes.

notes: one or two short plain sentences about anything you could NOT match (e.g. "Only 2 ground beef recipes are saved, so I planned 2 instead of 3."). Use an empty string when everything was met.

ALREADY ON HER PLANNER:
{planned}

HER RECIPE LIBRARY (id | name | category | meal_type | total time | ★ = favorite | key ingredients):
{catalog}
"""


class MealPlanningMixin:
    """Mixin that plans meals from saved recipes and adds them to the planner."""

    def _add_meals_to_planner(
        self,
        args: dict,
        context_data: Optional[dict],
        contents: list,
        model_turn=None,
        load_recipe_catalog: Optional[RecipeCatalogLoader] = None,
        add_planner_meals: Optional[PlannerMealAdder] = None,
    ) -> dict:
        """Plan the requested meals, write them to the planner, then confirm the outcome.

        A dedicated planning call picks mains and sides from the recipe library;
        its picks are validated against that library before anything is written,
        and Genie's reply is based on what actually landed.
        """
        if load_recipe_catalog is None or add_planner_meals is None:
            return {"type": "chat", "response": PLANNER_FAILED_REPLY, "tool_args": args}

        planned = (context_data or {}).get("meal_plan", [])
        open_slots = MAX_PLANNER_ENTRIES - len(planned)
        if open_slots <= 0:
            return {
                "type": "chat",
                "response": (
                    f"Your meal planner is full ({MAX_PLANNER_ENTRIES} meals) — mark a few "
                    "as cooked or clear some out and I'll happily fill it back up! 📅"
                ),
                "tool_args": args,
            }

        try:
            catalog = load_recipe_catalog()
        except Exception:
            logger.exception("[Assistant] Failed to load the recipe catalog for planning")
            return {"type": "chat", "response": PLANNER_FAILED_REPLY, "tool_args": args}

        if not catalog:
            return {
                "type": "chat",
                "response": (
                    "You don't have any saved recipes for me to plan from yet — save a few "
                    "(or ask me to create some) and I'll build your menu! 🍳"
                ),
                "tool_args": args,
            }

        requested = max(1, safe_int(args.get("meal_count")) or 1)
        meal_count = min(requested, open_slots)
        requirements = str(args.get("requirements") or "").strip() or "Any well-rounded dinners."

        raw_plan = self._request_meal_plan(requirements, meal_count, catalog, planned)
        if raw_plan is None:
            return {
                "type": "chat",
                "response": (
                    "Hmm, I couldn't put that plan together just now — mind asking again "
                    "in a sec?"
                ),
                "tool_args": args,
            }

        catalog_by_id = {r["id"]: r for r in catalog}
        meals = self._parse_meal_plan(raw_plan.get("meals"), catalog_by_id, meal_count)
        notes = str(raw_plan.get("notes") or "").strip()

        if not meals:
            # Nothing in the library fit; explain why without claiming a write
            instruction = (
                "Nothing was added to her meal planner: none of her saved recipes fit "
                "the request. Explain the gap from 'notes' in 1-2 short sentences and "
                "offer to create a recipe that fits or to plan with looser rules. "
                "Use 1 emoji."
            )
            final_text = self._finalize_after_tool_call(
                contents,
                model_turn,
                "add_meals_to_planner",
                instruction,
                "I couldn't find saved recipes that fit that plan — want me to create "
                "one, or loosen the rules a bit?",
                result={"added_meals": [], "notes": notes},
            )
            return {"type": "chat", "response": final_text, "tool_args": args}

        try:
            entries = add_planner_meals(meals)
        except Exception as e:
            # Canned on purpose: a model-written reply here risks claiming success
            logger.warning(f"[Assistant] Adding planned meals failed: {e}")
            return {"type": "chat", "response": PLANNER_FAILED_REPLY, "tool_args": args}

        summary = {
            "added_meals": [
                {
                    "main": catalog_by_id[m.main_recipe_id]["name"],
                    "sides": [catalog_by_id[sid]["name"] for sid in m.side_recipe_ids],
                }
                for m in meals
            ],
            "notes": notes,
            "not_added_planner_full": requested - meal_count,
        }
        instruction = (
            "Confirm the meal planner update. Say how many meals were added, then list "
            "every meal in 'added_meals' as a markdown bullet: the main in bold, then "
            "its sides after a dash (e.g. '- **Beef Tacos** — Mexican Rice, Street "
            "Corn'). If 'notes' is not empty, mention that gap in one short sentence. "
            "If 'not_added_planner_full' is above 0, say that many didn't fit because "
            "her planner is full. Only mention meals from 'added_meals'. End by "
            "offering to swap anything out. Use 1-2 emojis."
        )
        final_text = self._finalize_after_tool_call(
            contents,
            model_turn,
            "add_meals_to_planner",
            instruction,
            self._describe_planner_update(summary),
            result=summary,
        )

        return {
            "type": "planner",
            "response": final_text,
            "planner_update": entries,
            "tool_args": args,
        }

    def _request_meal_plan(
        self,
        requirements: str,
        meal_count: int,
        catalog: List[dict],
        planned: List[dict],
    ) -> Optional[dict]:
        """Ask the model to pick mains and sides from the library.

        Returns:
            The parsed plan ({meals, notes}), or None if the call or parsing failed.
        """
        # Shuffled so repeat requests don't always land on the first matches
        catalog_lines = "\n".join(
            self._format_catalog_line(r) for r in random.sample(catalog, len(catalog))
        )
        planned_lines = "\n".join(
            f"- {p['meal_name']} ({p['main_recipe_name']})" for p in planned
        ) or "(nothing yet)"

        prompt = MEAL_PLAN_PROMPT.format(
            requirements=requirements,
            meal_count=meal_count,
            planned=planned_lines,
            catalog=catalog_lines,
        )

        try:
            client = get_gemini_client(API_KEY_ENV_VAR)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={
                    "temperature": PLAN_TEMPERATURE,
                    "response_mime_type": "application/json",
                    "response_schema": MEAL_PLAN_SCHEMA,
                },
            )
            raw_text = extract_text_from_response(response)
            data = json.loads(raw_text) if raw_text else None
        except Exception as e:  # API errors and malformed JSON alike
            logger.warning(f"[Assistant] Meal planning call failed: {e}")
            return None

        if not isinstance(data, dict):
            logger.warning(f"[Assistant] Meal planning returned no plan: {raw_text!r:.300}")
            return None
        return data

    @staticmethod
    def _format_catalog_line(recipe: dict) -> str:
        """One compact library line for the planning prompt."""
        time_str = f"{recipe['total_time']}min" if recipe.get("total_time") else "-"
        favorite = "★" if recipe.get("is_favorite") else ""
        ingredients = ", ".join(recipe.get("ingredients") or [])
        return (
            f"{recipe['id']} | {recipe['name']} | {recipe['category']} | "
            f"{recipe['meal_type']} | {time_str} | {favorite} | {ingredients}"
        )

    @staticmethod
    def _parse_meal_plan(
        raw_meals, catalog_by_id: dict, limit: int
    ) -> List[MealCreateDTO]:
        """Keep only meals built from real library recipes.

        Drops unknown ids and repeated mains, de-duplicates sides (never the main
        itself), caps sides per meal, and stops at ``limit`` meals. Each meal is
        named after its main recipe, matching how the planner names new meals.
        """
        meals: List[MealCreateDTO] = []
        used_mains: set[int] = set()
        for raw in raw_meals if isinstance(raw_meals, list) else []:
            if len(meals) >= limit:
                break
            if not isinstance(raw, dict):
                continue

            main_id = safe_int(raw.get("main_recipe_id"))
            if main_id not in catalog_by_id or main_id in used_mains:
                continue

            raw_sides = raw.get("side_recipe_ids")
            side_ids = [safe_int(s) for s in raw_sides] if isinstance(raw_sides, list) else []
            side_ids = [
                sid for sid in dict.fromkeys(side_ids)
                if sid in catalog_by_id and sid != main_id
            ][:MAX_SIDES_PER_MEAL]

            try:
                meal = MealCreateDTO(
                    meal_name=catalog_by_id[main_id]["name"],
                    main_recipe_id=main_id,
                    side_recipe_ids=side_ids,
                )
            except ValueError as e:  # pydantic ValidationError is a ValueError
                logger.warning(f"[Assistant] Skipping invalid planned meal {raw!r}: {e}")
                continue

            used_mains.add(main_id)
            meals.append(meal)
        return meals

    @staticmethod
    def _describe_planner_update(summary: dict) -> str:
        """Plain confirmation used when the model returns no follow-up text."""
        count = len(summary["added_meals"])
        lines = [f"Added {count} {'meal' if count == 1 else 'meals'} to your planner! 📅", ""]
        for meal in summary["added_meals"]:
            sides = f" — {', '.join(meal['sides'])}" if meal["sides"] else ""
            lines.append(f"- **{meal['main']}**{sides}")
        if summary["notes"]:
            lines += ["", summary["notes"]]
        return "\n".join(lines)
