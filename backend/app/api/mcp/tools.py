"""app/api/mcp/tools.py

Every MCP tool, one per thing a person can do in Enchanted Spoon.

A tool is a ``ToolSpec``: a name and description written for ChatGPT, the
app route it calls, and its hints. Its input schema is not written by hand:
it is built from the route's own OpenAPI (path and query parameters plus
the request body's fields), so a tool accepts exactly what the app accepts,
then given friendlier descriptions from ``params`` and ``PARAM_DOCS``.

Tools that spend AI allowance are marked as writes (they change the
account's usage counters), so ChatGPT asks before each one.

A few tools are composites (``handler``): ``get_overview`` reads several
pages at once, and ``generate_recipe_photo`` does what the app's "Generate
photo" button does (generate, upload, attach). They still only call routes.

Routes with no tool are listed in ``EXCLUDED`` with the reason;
tests/test_mcp_server.py fails when a route is in neither.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple

from fastapi import FastAPI

from app.api.mcp import dispatch

Kind = Literal["read", "write", "delete"]
Handler = Callable[["ToolContext", Dict[str, Any]], Awaitable[Any]]

AI_NOTE = "Calls AI generation (costs money and counts against the account's monthly AI allowance)."


@dataclass(frozen=True)
class ToolContext:
    """Who a tool call acts for, passed to composite handlers."""

    user_id: int
    authorization: Optional[str] = None

    async def call(self, method: str, path: str, **kwargs: Any) -> Any:
        """Call one app route as this user (see dispatch.call)."""
        return await dispatch.call(self.user_id, method, path, authorization=self.authorization, **kwargs)


@dataclass(frozen=True)
class ToolSpec:
    """One MCP tool.

    Attributes:
        name: snake_case tool name.
        description: For ChatGPT: what it does, when to use it, where ids come from.
        method: HTTP method of the route it calls (route tools).
        path: The route's path template, e.g. ``/api/recipes/{recipe_id}``.
        kind: read (no changes), write, or delete (removes or overwrites).
        idempotent: Repeating the call changes nothing more (defaults: reads and deletes yes).
        open_world: The tool reaches outside the app (feedback creates a support ticket).
        params: Per-argument description, or ``{"description":..., "enum": [...]}``.
        body_arg: Argument name for a request body that isn't an object (e.g. a list).
        hidden: Route arguments not offered to ChatGPT; ``fixed`` supplies them.
        fixed: Values always sent for hidden arguments.
        handler: Composite tools: an async function of (context, arguments).
        input_schema: Composite tools: their JSON schema.
        uses: Composite tools: every (method, path) they call.
        title: Human-readable name shown by clients.
    """

    name: str
    description: str
    kind: Kind
    method: Optional[str] = None
    path: Optional[str] = None
    idempotent: Optional[bool] = None
    open_world: bool = False
    params: Dict[str, Any] = field(default_factory=dict)
    body_arg: Optional[str] = None
    hidden: Tuple[str, ...] = ()
    fixed: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Handler] = None
    input_schema: Optional[Dict[str, Any]] = None
    uses: Tuple[Tuple[str, str], ...] = ()
    title: Optional[str] = None

    @property
    def endpoints(self) -> Tuple[Tuple[str, str], ...]:
        """Every (method, path) this tool calls."""
        if self.method and self.path:
            return ((self.method, self.path),)
        return self.uses

    @property
    def display_title(self) -> str:
        """Human-readable name (the tool's ``title``)."""
        return self.title or self.name.replace("_", " ").capitalize()

    def annotations(self) -> Dict[str, Any]:
        """MCP tool annotations (ChatGPT asks before running anything not read-only)."""
        idempotent = self.idempotent if self.idempotent is not None else self.kind in ("read", "delete")
        return {
            "readOnlyHint": self.kind == "read",
            "destructiveHint": self.kind == "delete",
            "idempotentHint": idempotent,
            "openWorldHint": self.open_world,
        }


# Descriptions for common arguments whose route schema has none.
PARAM_DOCS: Dict[str, str] = {
    "recipe_id": "Recipe id (from list_recipes or search_recipes).",
    "meal_id": "Meal id (from list_meals or list_planner_entries).",
    "entry_id": "Planner entry id (from list_planner_entries; not the meal id).",
    "item_id": "Shopping list item id (from get_shopping_list).",
    "group_id": "Recipe collection id (from list_recipe_groups).",
    "ingredient_id": "Ingredient id (from list_ingredients).",
    "rule_id": "Unit conversion rule id (from list_unit_conversions).",
    "invite_id": "Invite id (from get_household).",
    "member_user_id": "The member's user id (from get_household).",
    "limit": "Maximum number of results.",
    "offset": "Number of results to skip, for paging.",
    "search_term": "Text to search for in names.",
    "include_disabled": "Also include hidden (disabled) entries.",
    "tz": "IANA time zone used to decide which day a meal was cooked, e.g. America/New_York.",
}


async def _overview(ctx: ToolContext, _args: Dict[str, Any]) -> Dict[str, Any]:
    """Account, counts and this week's plan in one read."""
    return {
        "account": await ctx.call("GET", "/api/users/me"),
        "stats": await ctx.call("GET", "/api/dashboard/stats"),
        "planner": await ctx.call("GET", "/api/planner/summary"),
    }


async def _generate_photo(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """The app's Generate photo: make a square photo, upload it, set it as the recipe's image.

    The banner uses the same square image; the app crops it to 21:9.
    """
    recipe_id = args.get("recipe_id")
    if not isinstance(recipe_id, int):
        raise dispatch.ToolCallError("recipe_id (an integer) is required.")
    recipe = await ctx.call("GET", f"/api/recipes/{recipe_id}")
    request: Dict[str, Any] = {"recipe_name": recipe["recipe_name"]}
    if args.get("custom_prompt"):
        request["custom_prompt"] = args["custom_prompt"]
    generated = await ctx.call("POST", "/api/ai/image-generation", json_body=request)
    if not generated or not generated.get("success") or not generated.get("reference_image_data"):
        raise dispatch.ToolCallError((generated or {}).get("error") or "The photo couldn't be generated.")
    uploaded = await ctx.call(
        "POST",
        "/api/upload/base64",
        form={"image_data": generated["reference_image_data"], "recipeId": str(recipe_id), "imageType": "reference"},
    )
    url = uploaded.get("path") if isinstance(uploaded, dict) else None
    if not url:
        raise dispatch.ToolCallError("The photo was generated but couldn't be uploaded.")
    updated = await ctx.call(
        "PUT", f"/api/recipes/{recipe_id}", json_body={"reference_image_path": url, "banner_image_path": url}
    )
    return {"recipe_id": recipe_id, "recipe_name": updated.get("recipe_name"), "image_url": url}


def _categories(prefix: str, noun: str, plural: str, used_for: str) -> List[ToolSpec]:
    """The eight tools for a customisable label list (recipe categories, ingredient categories, units)."""
    base = f"/api/{prefix}"
    id_name = "unit_id" if prefix == "ingredient-units" else "category_id"
    id_doc = f"{noun.capitalize()} id (from list_{plural})."
    snake = plural  # e.g. recipe_categories
    single = snake[:-3] + "y" if snake.endswith("ies") else snake[:-1]
    return [
        ToolSpec(f"list_{snake}", f"List the {plural.replace('_', ' ')} offered when {used_for}, in display order.", "read", "GET", base),
        ToolSpec(f"get_{single}", f"Get one {noun} by id.", "read", "GET", f"{base}/{{{id_name}}}", params={id_name: id_doc}),
        ToolSpec(f"create_{single}", f"Add a custom {noun}.", "write", "POST", base, params={"label": f"The {noun}'s name as shown in the app."}),
        ToolSpec(
            f"update_{single}",
            f"Rename a {noun} or show/hide it (is_enabled).",
            "write",
            "PUT",
            f"{base}/{{{id_name}}}",
            idempotent=True,
            params={id_name: id_doc},
        ),
        ToolSpec(f"delete_{single}", f"Delete a custom {noun}. Built-in ones can only be hidden (update with is_enabled=false).", "delete", "DELETE", f"{base}/{{{id_name}}}", params={id_name: id_doc}),
        ToolSpec(
            f"reorder_{snake}",
            f"Set the display order of {plural.replace('_', ' ')}: pass every id in the new order.",
            "write",
            "PUT",
            f"{base}/reorder",
            idempotent=True,
            params={"ordered_ids": f"All {noun} ids, in the order to show them."},
        ),
        ToolSpec(
            f"bulk_update_{snake}",
            f"Change several {plural.replace('_', ' ')} at once (labels, shown/hidden, order) in one call.",
            "write",
            "PUT",
            f"{base}/bulk",
            idempotent=True,
        ),
        ToolSpec(
            f"reset_{snake}",
            f"Reset {plural.replace('_', ' ')} to the app's defaults, discarding custom ones and custom order.",
            "delete",
            "POST",
            f"{base}/reset",
        ),
    ]


TOOLS: List[ToolSpec] = [
    # ── Overview & account ──────────────────────────────────────────────────
    ToolSpec(
        "get_overview",
        "Start here: the account (name, plan), recipe/meal counts and a summary of the meal planner.",
        "read",
        handler=_overview,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        uses=(("GET", "/api/users/me"), ("GET", "/api/dashboard/stats"), ("GET", "/api/planner/summary")),
    ),
    ToolSpec("get_ai_usage", "This month's AI usage and limits for the account (recipe generation, photos, Genie chat...).", "read", "GET", "/api/users/me/usage"),

    # ── Recipes ─────────────────────────────────────────────────────────────
    ToolSpec(
        "list_recipes",
        "List or search recipes as short cards (id, name, category, times, favorite). Use this to find recipe ids.",
        "read",
        "GET",
        "/api/recipes/cards",
        params={
            "search_term": "Text to look for in recipe names.",
            "recipe_category": "Only this category (see list_recipe_categories).",
            "meal_type": "Only this meal type, e.g. Dinner (see list_meal_types_in_use).",
            "favorites_only": "Only favorite recipes.",
            "limit": "Maximum number of recipes (1-100).",
        },
    ),
    ToolSpec(
        "search_recipes",
        "Search recipes with full details (ingredients, directions) and more filters and sorting. Prefer list_recipes for browsing.",
        "read",
        "GET",
        "/api/recipes",
        params={
            "cook_time": "Maximum cook time in minutes.",
            "servings": "Minimum servings.",
            "diet_pref": "Diet preference, e.g. Vegetarian.",
            "sort_by": {"description": "Sort field.", "enum": ["recipe_name", "created_at", "total_time", "servings"]},
            "sort_order": {"description": "Sort direction.", "enum": ["asc", "desc"]},
            "limit": "Maximum number of recipes (1-100).",
        },
    ),
    ToolSpec("get_recipe", "Get one recipe in full: ingredients, directions, notes, times, nutrition and image links.", "read", "GET", "/api/recipes/{recipe_id}"),
    ToolSpec(
        "create_recipe",
        "Save a new recipe. Times are minutes; directions are plain text, one step per line; difficulty is Easy, Medium or Hard. "
        "Use the drafts from generate_recipe or import_recipe_from_url here to save them.",
        "write",
        "POST",
        "/api/recipes",
        params={
            "recipe_category": "Category name (see list_recipe_categories), e.g. Italian.",
            "meal_type": "e.g. Breakfast, Lunch, Dinner, Side, Dessert, Snack.",
            "ingredients": "Ingredients: name, category (shopping aisle, e.g. Produce, Dairy), quantity and unit.",
            "is_ai_generated": "True when the recipe came from AI generation.",
        },
    ),
    ToolSpec(
        "update_recipe",
        "Change a recipe. Send only the fields to change; sending ingredients replaces the whole ingredient list.",
        "write",
        "PUT",
        "/api/recipes/{recipe_id}",
        idempotent=True,
    ),
    ToolSpec(
        "delete_recipe",
        "Delete a recipe permanently. Check get_recipe_deletion_impact first: meals built on it are affected.",
        "delete",
        "DELETE",
        "/api/recipes/{recipe_id}",
    ),
    ToolSpec("get_recipe_deletion_impact", "Which meals and planner entries would be affected if a recipe were deleted.", "read", "GET", "/api/recipes/{recipe_id}/deletion-impact"),
    ToolSpec("get_recipe_last_cooked", "When a recipe was last cooked (from completed planner entries).", "read", "GET", "/api/recipes/{recipe_id}/last-cooked"),
    ToolSpec("toggle_recipe_favorite", "Flip a recipe's favorite flag (favorite <-> not). Check is_favorite with get_recipe first.", "write", "POST", "/api/recipes/{recipe_id}/favorite"),
    ToolSpec("list_recipe_category_names_in_use", "The category names used by the account's recipes.", "read", "GET", "/api/recipes/categories"),
    ToolSpec("list_meal_types_in_use", "The meal types used by the account's recipes (e.g. Dinner, Side).", "read", "GET", "/api/recipes/meal-types"),

    # ── Recipe collections (groups) ─────────────────────────────────────────
    ToolSpec("list_recipe_groups", "List recipe collections (groups/folders) with the recipes in each.", "read", "GET", "/api/recipe-groups"),
    ToolSpec("get_recipe_group", "Get one recipe collection and its recipes.", "read", "GET", "/api/recipe-groups/{group_id}"),
    ToolSpec("create_recipe_group", "Create a recipe collection.", "write", "POST", "/api/recipe-groups", params={"name": "Collection name."}),
    ToolSpec("rename_recipe_group", "Rename a recipe collection.", "write", "PUT", "/api/recipe-groups/{group_id}", idempotent=True),
    ToolSpec("delete_recipe_group", "Delete a recipe collection. The recipes in it are kept.", "delete", "DELETE", "/api/recipe-groups/{group_id}"),
    ToolSpec("list_groups_for_recipe", "Which collections a recipe is in.", "read", "GET", "/api/recipe-groups/by-recipe/{recipe_id}"),
    ToolSpec(
        "set_recipe_groups",
        "Put a recipe in exactly these collections (replaces its current collections; an empty list removes it from all).",
        "write",
        "PUT",
        "/api/recipe-groups/by-recipe/{recipe_id}/assign",
        idempotent=True,
        params={"group_ids": "Collection ids (from list_recipe_groups)."},
    ),
    ToolSpec("add_recipe_to_group", "Add a recipe to a collection.", "write", "POST", "/api/recipe-groups/{group_id}/recipes/{recipe_id}", idempotent=True),
    ToolSpec("remove_recipe_from_group", "Take a recipe out of a collection (the recipe is kept).", "write", "DELETE", "/api/recipe-groups/{group_id}/recipes/{recipe_id}", idempotent=True),

    # ── Meals ───────────────────────────────────────────────────────────────
    ToolSpec(
        "list_meals",
        "List meals (a main recipe plus up to 3 sides). Saved meals are the reusable ones in the meal library.",
        "read",
        "GET",
        "/api/meals",
        params={"name_pattern": "Text to look for in meal names.", "tags": "Only meals with these tags.", "saved": "True for saved meals only."},
    ),
    ToolSpec("get_meal", "Get one meal with its main and side recipes.", "read", "GET", "/api/meals/{meal_id}"),
    ToolSpec("list_meals_with_recipe", "Meals that use a recipe as main or side.", "read", "GET", "/api/meals/by-recipe/{recipe_id}"),
    ToolSpec(
        "create_meal",
        "Create a meal from a main recipe and up to 3 side recipes (ids from list_recipes). Then add it to the planner with add_meal_to_planner.",
        "write",
        "POST",
        "/api/meals",
        params={"is_saved": "Keep it in the saved-meal library (default false).", "tags": "Up to 20 short tags."},
    ),
    ToolSpec("update_meal", "Change a meal's name, main recipe, sides, tags or saved flag. Send only what changes.", "write", "PUT", "/api/meals/{meal_id}", idempotent=True),
    ToolSpec("delete_meal", "Delete a meal (and its planner entries). Its recipes are kept.", "delete", "DELETE", "/api/meals/{meal_id}"),
    ToolSpec("toggle_meal_saved", "Flip whether a meal is kept in the saved-meal library.", "write", "POST", "/api/meals/{meal_id}/save"),
    ToolSpec("add_side_to_meal", "Add a side recipe to a meal (3 sides at most).", "write", "POST", "/api/meals/{meal_id}/sides/{recipe_id}"),
    ToolSpec("remove_side_from_meal", "Remove a side recipe from a meal.", "write", "DELETE", "/api/meals/{meal_id}/sides/{recipe_id}", idempotent=True),
    ToolSpec(
        "reorder_meal_sides",
        "Set the order of a meal's side recipes.",
        "write",
        "PUT",
        "/api/meals/{meal_id}/sides/reorder",
        idempotent=True,
        body_arg="side_recipe_ids",
        params={"side_recipe_ids": "The meal's side recipe ids in the new order."},
    ),

    # ── Meal planner ────────────────────────────────────────────────────────
    ToolSpec(
        "list_planner_entries",
        "The Menu (meal planner): the meals planned, in order, with whether each is cooked and how it feeds the shopping list.",
        "read",
        "GET",
        "/api/planner/entries",
        params={"meal_id": "Only entries for this meal.", "completed": "True for cooked entries only, false for not yet cooked."},
    ),
    ToolSpec("get_planner_entry", "Get one planner entry.", "read", "GET", "/api/planner/entries/{entry_id}"),
    ToolSpec("get_planner_summary", "Counts for the planner: planned, cooked, remaining.", "read", "GET", "/api/planner/summary"),
    ToolSpec("list_planned_meal_ids", "Ids of every meal currently in the planner.", "read", "GET", "/api/planner/meal-ids"),
    ToolSpec("get_cooking_streak", "The cooking streak: days in a row with a meal cooked.", "read", "GET", "/api/planner/streak"),
    ToolSpec(
        "add_meal_to_planner",
        "Add a meal to the Menu (meal planner; 20 uncooked meals at most). The shopping list updates from planned meals.",
        "write",
        "POST",
        "/api/planner/entries/{meal_id}",
    ),
    ToolSpec("add_meals_to_planner", "Add several meals to the planner at once.", "write", "POST", "/api/planner/entries/bulk", params={"meal_ids": "Meal ids (from list_meals)."}),
    ToolSpec(
        "reorder_planner",
        "Set the order of the planner: pass every entry id in the new order.",
        "write",
        "PUT",
        "/api/planner/entries/reorder",
        idempotent=True,
        params={"entry_ids": "All planner entry ids, in the new order."},
    ),
    ToolSpec("mark_planner_entry_cooked", "Mark a planned meal as cooked (counts toward the streak and cooking history).", "write", "POST", "/api/planner/entries/{entry_id}/complete", idempotent=True),
    ToolSpec("mark_planner_entry_not_cooked", "Undo marking a planned meal as cooked.", "write", "POST", "/api/planner/entries/{entry_id}/incomplete", idempotent=True),
    ToolSpec(
        "set_planner_entry_shopping_mode",
        "Choose what a planned meal adds to the shopping list: all ingredients, produce only, or nothing.",
        "write",
        "PUT",
        "/api/planner/entries/{entry_id}/shopping-mode",
        idempotent=True,
    ),
    ToolSpec("remove_planner_entry", "Take one entry off the planner (the meal itself is kept).", "delete", "DELETE", "/api/planner/entries/{entry_id}"),
    ToolSpec("remove_meal_from_planner", "Take every planner entry for a meal off the planner.", "delete", "DELETE", "/api/planner/entries/by-meal/{meal_id}"),
    ToolSpec("clear_planner", "Remove every entry from the Menu (meal planner).", "delete", "DELETE", "/api/planner/clear"),
    ToolSpec("clear_cooked_from_planner", "Remove the entries already marked cooked from the planner.", "delete", "DELETE", "/api/planner/clear-completed"),

    # ── Shopping list ───────────────────────────────────────────────────────
    ToolSpec(
        "get_shopping_list",
        "The shopping list, grouped by aisle category, with what's already in the cart ('have'). Items come from planned meals and manual adds.",
        "read",
        "GET",
        "/api/shopping",
        params={
            "source": {"description": "Only items from planned recipes or manual adds.", "enum": ["recipe", "manual"]},
            "category": "Only this aisle category, e.g. Produce.",
            "have": "True for items already got, false for items still needed.",
            "auto_generate": "Refresh recipe items from the planner first (default true).",
        },
    ),
    ToolSpec("get_shopping_item", "Get one shopping list item.", "read", "GET", "/api/shopping/items/{item_id}"),
    ToolSpec(
        "add_shopping_item",
        "Add an item to the shopping list by hand.",
        "write",
        "POST",
        "/api/shopping/items",
        params={"ingredient_name": "What to buy, e.g. Milk.", "quantity": "How much (a number).", "unit": "Unit, e.g. lb, cup, can.", "category": "Aisle category, e.g. Dairy."},
    ),
    ToolSpec(
        "update_shopping_item",
        "Change a shopping list item: name, quantity, unit, category, have (got it) or flagged. Send only what changes.",
        "write",
        "PATCH",
        "/api/shopping/items/{item_id}",
        idempotent=True,
        params={"have": "True when it's been bought or is in the cart.", "flagged": "True to flag the item (e.g. couldn't find it)."},
    ),
    ToolSpec(
        "set_shopping_items_have",
        "Mark several shopping list items as got (true) or still needed (false) at once.",
        "write",
        "PATCH",
        "/api/shopping/bulk-update",
        idempotent=True,
        params={"item_updates": 'Map of item id to have, e.g. {"12": true, "15": false}.'},
    ),
    ToolSpec("delete_shopping_item", "Remove one item from the shopping list.", "delete", "DELETE", "/api/shopping/items/{item_id}"),
    ToolSpec(
        "generate_shopping_list",
        "Build shopping list items from specific recipes' ingredients.",
        "write",
        "POST",
        "/api/shopping/generate",
        params={
            "recipe_ids": "Recipe ids (from list_recipes).",
            "include_manual_items": "Keep items added by hand.",
            "clear_existing": "Clear the current recipe items first.",
        },
    ),
    ToolSpec("sync_shopping_list_from_planner", "Refresh the shopping list's recipe items from the meals in the planner now.", "write", "POST", "/api/shopping/generate-from-planner", idempotent=True),
    ToolSpec("get_shopping_breakdown", "Which recipes need each shopping list ingredient, for the given recipes.", "read", "GET", "/api/shopping/breakdown", params={"recipe_ids": "Comma-separated recipe ids, e.g. 3,7,9."}),
    ToolSpec("get_shopping_notes", "The free-text notes pad on the shopping list.", "read", "GET", "/api/shopping/notes"),
    ToolSpec("set_shopping_notes", "Replace the shopping list's free-text notes (send the full new text).", "write", "PUT", "/api/shopping/notes", idempotent=True),
    ToolSpec("clear_shopping_list", "Remove every item from the shopping list.", "delete", "DELETE", "/api/shopping/clear"),
    ToolSpec("clear_manual_shopping_items", "Remove only the items added by hand.", "delete", "DELETE", "/api/shopping/clear-manual"),
    ToolSpec("clear_recipe_shopping_items", "Remove only the items that came from recipes.", "delete", "DELETE", "/api/shopping/clear-recipe"),
    ToolSpec("clear_checked_shopping_items", "Remove the items already marked as got.", "delete", "DELETE", "/api/shopping/clear-completed"),

    # ── Ingredients library ─────────────────────────────────────────────────
    ToolSpec("list_ingredients", "List or search the ingredient library (names and aisle categories used in recipes).", "read", "GET", "/api/ingredients", params={"category": "Only this aisle category."}),
    ToolSpec("get_ingredient", "Get one ingredient from the library.", "read", "GET", "/api/ingredients/{ingredient_id}"),
    ToolSpec("list_ingredient_names", "Every ingredient name in the library (for spelling matches).", "read", "GET", "/api/ingredients/names"),
    ToolSpec("list_ingredient_category_names_in_use", "The aisle categories used by ingredients in the library.", "read", "GET", "/api/ingredients/categories"),
    ToolSpec("create_ingredient", "Add an ingredient to the library (returns the existing one if the name is already there).", "write", "POST", "/api/ingredients", idempotent=True),
    ToolSpec(
        "create_ingredients",
        "Add several ingredients to the library at once (existing names are returned as they are).",
        "write",
        "POST",
        "/api/ingredients/bulk",
        idempotent=True,
        body_arg="ingredients",
        params={"ingredients": "Ingredients to add, each with ingredient_name and ingredient_category."},
    ),
    ToolSpec("update_ingredient", "Rename an ingredient or change its aisle category.", "write", "PUT", "/api/ingredients/{ingredient_id}", idempotent=True),
    ToolSpec("delete_ingredient", "Delete an ingredient from the library.", "delete", "DELETE", "/api/ingredients/{ingredient_id}"),

    # ── Unit conversions ────────────────────────────────────────────────────
    ToolSpec("list_units", "The measurement units the app knows (for quantities and conversion rules).", "read", "GET", "/api/unit-conversions/units"),
    ToolSpec("list_unit_conversions", "The account's unit conversion rules (e.g. 1 clove garlic = 0.5 tsp), used to combine shopping list quantities.", "read", "GET", "/api/unit-conversions"),
    ToolSpec("get_unit_conversion", "Get one unit conversion rule.", "read", "GET", "/api/unit-conversions/{rule_id}"),
    ToolSpec(
        "create_unit_conversion",
        "Add a conversion rule for an ingredient: 1 from_unit = factor to_unit.",
        "write",
        "POST",
        "/api/unit-conversions",
        params={"factor": "How many to_unit make one from_unit.", "round_up": "Round converted quantities up to whole units."},
    ),
    ToolSpec("update_unit_conversion", "Change a unit conversion rule.", "write", "PUT", "/api/unit-conversions/{rule_id}", idempotent=True),
    ToolSpec("delete_unit_conversion", "Delete a unit conversion rule.", "delete", "DELETE", "/api/unit-conversions/{rule_id}"),

    # ── Settings ────────────────────────────────────────────────────────────
    ToolSpec("get_settings", "The app settings: profile, appearance, recipe preferences, shopping list options, AI options.", "read", "GET", "/api/settings"),
    ToolSpec(
        "update_settings",
        "Change settings. Send only the sections and fields to change; the rest are kept.",
        "write",
        "PATCH",
        "/api/settings",
        idempotent=True,
        # App bookkeeping (install prompt, what's-new reads), not settings a person sets.
        hidden=("schemaVersion", "installPrompt", "whatsNew"),
    ),

    # ── Household ───────────────────────────────────────────────────────────
    ToolSpec("get_household", "The household (shared planner, shopping list and cookbook): members, invites, or null if not in one.", "read", "GET", "/api/household"),
    ToolSpec("create_household", "Start a household; the account becomes its owner.", "write", "POST", "/api/household"),
    ToolSpec("rename_household", "Rename the household (owner only).", "write", "PATCH", "/api/household", idempotent=True),
    ToolSpec("delete_household", "Delete the household (owner only). Recipes stay with whoever created them.", "delete", "DELETE", "/api/household"),
    ToolSpec(
        "create_household_invite",
        "Create an invite code for the household (owner only). No email is sent: share the code or link yourself.",
        "write",
        "POST",
        "/api/household/invites",
        params={"email": "Optional: who the invite is for, as a reminder."},
    ),
    ToolSpec("revoke_household_invite", "Cancel an unused invite (owner only).", "delete", "DELETE", "/api/household/invites/{invite_id}"),
    ToolSpec("join_household", "Join a household with an invite code.", "write", "POST", "/api/household/join", params={"code": "The invite code."}),
    ToolSpec("leave_household", "Leave the household. An owner must transfer ownership or remove the others first.", "delete", "POST", "/api/household/leave"),
    ToolSpec("remove_household_member", "Remove a member from the household (owner only).", "delete", "DELETE", "/api/household/members/{member_user_id}"),
    ToolSpec(
        "transfer_household_ownership",
        "Make another member the household owner; the shared planner and shopping list go with it.",
        "write",
        "POST",
        "/api/household/transfer",
        params={"user_id": "The member's user id (from get_household)."},
    ),
    ToolSpec("share_recipe_with_household", "Put one of the account's recipes in the household cookbook.", "write", "POST", "/api/household/recipes/{recipe_id}/share", idempotent=True),
    ToolSpec("unshare_recipe_from_household", "Take a recipe out of the household cookbook (the recipe is kept).", "write", "DELETE", "/api/household/recipes/{recipe_id}/share", idempotent=True),

    # ── Starter pack ────────────────────────────────────────────────────────
    ToolSpec("get_sample_data_status", "Whether the account still has the untouched sample recipes and meals from sign-up.", "read", "GET", "/api/sample-data"),
    ToolSpec("add_sample_data", "Add the starter pack of sample recipes, meals and a sample plan to the account.", "write", "POST", "/api/sample-data"),
    ToolSpec("remove_sample_data", "Remove the untouched sample recipes and meals (and their planner entries).", "delete", "DELETE", "/api/sample-data"),

    # ── Feedback ────────────────────────────────────────────────────────────
    ToolSpec(
        "send_feedback",
        "Send feedback to the Enchanted Spoon team. Don't include private information.",
        "write",
        "POST",
        "/api/feedback",
        open_world=True,
        params={
            "category": {"description": "Kind of feedback.", "enum": ["Feature Request", "Bug Report", "General Feedback", "Question"]},
            "message": "The feedback, in the person's words.",
        },
        hidden=("metadata",),
    ),

    # ── AI features ─────────────────────────────────────────────────────────
    ToolSpec(
        "generate_recipe",
        f"Write a new recipe from a description, e.g. 'quick vegetarian chili for 4'. Returns a draft (not saved): "
        f"show it, then save it with create_recipe (is_ai_generated true). {AI_NOTE}",
        "write",
        "POST",
        "/api/ai/wizard-generation",
        params={
            "prompt": "What to make, in plain words (up to 500 characters).",
            "allowed_categories": "Category names the recipe may use (from list_recipe_categories).",
            "estimate_nutrition": "Also estimate nutrition facts.",
        },
        hidden=("generate_image",),
        fixed={"generate_image": False},
    ),
    ToolSpec(
        "import_recipe_from_url",
        "Read a recipe from a web page, TikTok or Instagram link. Returns a draft (not saved): save it with create_recipe "
        f"(pass source_url). May use AI to read the page. {AI_NOTE}",
        "write",
        "POST",
        "/api/ai/recipe-import",
        params={
            "url": "The recipe's link.",
            "allowed_categories": "Category names the recipe may use (from list_recipe_categories).",
            "pasted_text": "Optional: the recipe text (e.g. a video caption) when the page can't be read.",
        },
        hidden=("include_source_image",),
        fixed={"include_source_image": False},
    ),
    ToolSpec(
        "generate_recipe_photo",
        f"Create an AI food photo for a saved recipe and set it as the recipe's image (replaces the current one). {AI_NOTE}",
        "write",
        handler=_generate_photo,
        input_schema={
            "type": "object",
            "properties": {
                "recipe_id": {"type": "integer", "description": PARAM_DOCS["recipe_id"]},
                "custom_prompt": {
                    "type": "string",
                    "maxLength": 500,
                    "description": "Optional photo prompt; must include {recipe_name}. Leave out to use the account's default.",
                },
            },
            "required": ["recipe_id"],
            "additionalProperties": False,
        },
        uses=(
            ("GET", "/api/recipes/{recipe_id}"),
            ("POST", "/api/ai/image-generation"),
            ("POST", "/api/upload/base64"),
            ("PUT", "/api/recipes/{recipe_id}"),
        ),
    ),
    ToolSpec(
        "chat_with_genie",
        f"Ask Genie, the app's own cooking assistant, which can also add to the shopping list and planner. "
        f"Only use it when asked for Genie; otherwise use the other tools directly. {AI_NOTE}",
        "write",
        "POST",
        "/api/ai/assistant/chat",
        params={"message": "The message to Genie.", "conversation_history": "Earlier messages in this Genie conversation, oldest first."},
    ),
    ToolSpec(
        "suggest_sides",
        f"Suggest side dishes and a cooking tip for a main recipe. {AI_NOTE}",
        "write",
        "POST",
        "/api/ai/meal-suggestions",
    ),
    ToolSpec(
        "estimate_nutrition",
        f"Estimate nutrition facts for a recipe from its ingredients (not saved; pass the result to update_recipe as nutrition_facts to keep it). {AI_NOTE}",
        "write",
        "POST",
        "/api/ai/nutrition-estimation",
    ),
    ToolSpec("get_cooking_tip", f"A random cooking tip. {AI_NOTE}", "write", "GET", "/api/ai/cooking-tip"),
]

TOOLS += _categories("categories", "recipe category", "recipe_categories", "saving a recipe")
TOOLS += _categories("ingredient-categories", "ingredient category", "ingredient_categories", "sorting the shopping list by aisle")
TOOLS += _categories("ingredient-units", "ingredient unit", "ingredient_units", "entering ingredient quantities")


# Routes with no tool, and why. Prefixes first: none of these are things a
# person does in the app.
EXCLUDED_PREFIXES: Dict[str, str] = {
    "/api/admin": "admin-only pages",
    "/api/hearth": "the Hearth wall display's integration (X-API-Key)",
    "/api/webhooks": "payment provider webhooks",
    "/api/internal": "server-to-server push dispatch",
    "/api/devices": "native-app push notification tokens",
    "/api/oauth": "the connector's own sign-in",
    "/.well-known": "the connector's own discovery",
}

EXCLUDED: Dict[Tuple[str, str], str] = {
    ("DELETE", "/api/users/me"): "account deletion stays in the app",
    ("POST", "/api/users/me/sunset-notice"): "records that a one-time pop-up was seen (UI only)",
    ("GET", "/api/users/me"): "covered by get_overview",
    ("GET", "/api/dashboard/stats"): "covered by get_overview",
    ("PUT", "/api/settings"): "update_settings (PATCH) changes settings without resetting the rest",
    ("POST", "/api/shopping/external/items"): "Tada's integration endpoint (X-API-Key)",
    ("PATCH", "/api/shopping/items/{item_id}/toggle"): "update_shopping_item sets have directly",
    ("PATCH", "/api/shopping/items/{item_id}/toggle-flag"): "update_shopping_item sets flagged directly",
    ("POST", "/api/planner/entries/{entry_id}/cycle-shopping-mode"): "set_planner_entry_shopping_mode sets it directly",
    ("POST", "/api/ingredients/search"): "list_ingredients takes search_term",
    ("POST", "/api/upload"): "a file upload from the device; generate_recipe_photo covers photos",
    ("POST", "/api/ai/recipe-import/photo"): "photo upload from the device; ChatGPT can't send the files",
    ("POST", "/api/ai/image-generation/banner"): "retired: banners are cropped from the square photo",
    ("POST", "/api/ai/assistant/ask"): "older Genie endpoint the app no longer uses (chat_with_genie)",
    ("POST", "/api/ai/assistant/generate-recipe"): "older Genie endpoint the app no longer uses (generate_recipe)",
    ("POST", "/api/data-management/import/preview"): "spreadsheet upload from the device",
    ("POST", "/api/data-management/import/execute"): "spreadsheet upload from the device",
    ("GET", "/api/data-management/export"): "spreadsheet file download",
    ("GET", "/api/data-management/template"): "spreadsheet file download",
    ("GET", "/api/data-management/backup/full"): "backup file download",
    ("POST", "/api/data-management/restore/preview"): "backup file upload from the device",
    ("POST", "/api/data-management/restore/execute"): "backup file upload from the device",
    ("DELETE", "/api/data-management/clear-all"): "wipes the whole account (like account deletion); stays in the app",
    ("GET", "/api/billing/founder-offer"): "billing page marketing",
    ("POST", "/api/billing/checkout-session"): "payment happens in the browser",
    ("POST", "/api/billing/portal-session"): "payment happens in the browser",
    ("POST", "/api/billing/store/sync"): "app store purchases happen on the phone",
}


def _no_titles(node: Any, defs: Dict[str, Any]) -> Any:
    """Inline ``$ref``s, drop Pydantic's generated titles, and turn ``anyOf [T, null]`` into T."""
    if isinstance(node, list):
        return [_no_titles(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        siblings = {k: v for k, v in node.items() if k != "$ref"}
        return _no_titles({**copy.deepcopy(defs[ref.rsplit("/", 1)[-1]]), **siblings}, defs)
    out = {k: _no_titles(v, defs) for k, v in node.items() if not (k == "title" and isinstance(v, str))}
    options = out.get("anyOf")
    if isinstance(options, list):
        non_null = [o for o in options if o != {"type": "null"}]
        if len(non_null) == 1 and len(non_null) < len(options):
            merged = {**non_null[0], **{k: v for k, v in out.items() if k != "anyOf"}}
            return merged
    return out


@dataclass
class BuiltTool:
    """A tool ready to list and call: schema plus where each argument goes."""

    spec: ToolSpec
    schema: Dict[str, Any]
    path_args: List[str] = field(default_factory=list)
    query_args: List[str] = field(default_factory=list)
    body_args: List[str] = field(default_factory=list)


def build(app: FastAPI) -> Dict[str, BuiltTool]:
    """Build every tool's input schema from ``app``'s OpenAPI.

    Raises:
        ValueError: A tool names a route that doesn't exist, or an argument
            name is both a parameter and a body field.
    """
    openapi = app.openapi()
    defs = openapi.get("components", {}).get("schemas", {})
    built: Dict[str, BuiltTool] = {}
    for spec in TOOLS:
        if spec.name in built:
            raise ValueError(f"Duplicate tool name {spec.name}")
        if spec.handler is not None:
            built[spec.name] = BuiltTool(spec=spec, schema=copy.deepcopy(spec.input_schema or {"type": "object", "properties": {}}))
            continue
        op = openapi.get("paths", {}).get(spec.path or "", {}).get((spec.method or "").lower())
        if op is None:
            raise ValueError(f"Tool {spec.name}: no route {spec.method} {spec.path}")
        tool = BuiltTool(spec=spec, schema={})
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for param in op.get("parameters", []):
            where, name = param.get("in"), param["name"]
            if where not in ("path", "query") or name in spec.hidden:
                continue
            schema = _no_titles(param.get("schema", {}), defs)
            if param.get("description"):
                schema.setdefault("description", param["description"])
            properties[name] = schema
            if param.get("required"):
                required.append(name)
            (tool.path_args if where == "path" else tool.query_args).append(name)
        body = op.get("requestBody")
        if body:
            content = body.get("content", {})
            if "application/json" not in content:
                raise ValueError(f"Tool {spec.name}: body isn't JSON")
            body_schema = _no_titles(content["application/json"].get("schema", {}), defs)
            if spec.body_arg:
                properties[spec.body_arg] = body_schema
                if body.get("required"):
                    required.append(spec.body_arg)
                tool.body_args.append(spec.body_arg)
            else:
                for name, schema in body_schema.get("properties", {}).items():
                    if name in spec.hidden:
                        continue
                    if name in properties:
                        raise ValueError(f"Tool {spec.name}: {name} is both a parameter and a body field")
                    properties[name] = schema
                    tool.body_args.append(name)
                required += [n for n in body_schema.get("required", []) if n not in spec.hidden]
        for name, schema in properties.items():
            doc = spec.params.get(name)
            if isinstance(doc, dict):
                schema.update(doc)
            elif isinstance(doc, str):
                schema["description"] = doc
            elif name in PARAM_DOCS and "description" not in schema:
                schema["description"] = PARAM_DOCS[name]
        tool.schema = {"type": "object", "properties": properties, "additionalProperties": False}
        if required:
            tool.schema["required"] = sorted(set(required), key=required.index)
        built[spec.name] = tool
    return built
