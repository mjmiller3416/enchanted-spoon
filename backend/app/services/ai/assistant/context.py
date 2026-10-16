"""User context building and conditional context loading for the AI assistant.

Provides keyword detection for smart context loading and functions to build
formatted user context sections for the AI prompt.
"""

from typing import Optional

# ============================================================================
# KEYWORD DETECTION FOR CONDITIONAL CONTEXT LOADING
# ============================================================================

# When to load recipe ingredients
INGREDIENT_QUERY_KEYWORDS = [
    "what can i make with",
    "i have",
    "i've got",
    "using",
    "use up",
    "leftover",
    "in my fridge",
    "in my pantry",
    "with these ingredients",
    "ingredients i have",
    "based on what i have",
    "from what's in",
]

# When to load shopping list
SHOPPING_LIST_KEYWORDS = [
    "shopping list",
    "grocery list",
    "groceries",
    "to my list",
    "to the list",
    "on my list",
    "on the list",
    "what i have",
    "what i've got",
    "from my list",
    "my ingredients",
    "available ingredients",
    "already have",
    "need to buy",
]


def should_include_ingredients(message: str, history: Optional[list] = None) -> bool:
    """Check if recipe ingredients should be loaded based on message content.

    Args:
        message: Current user message.
        history: Optional conversation history to check recent context.

    Returns:
        True if ingredients should be included in context, False otherwise.
    """
    text = message.lower()
    if history:
        for entry in history[-4:]:
            if entry.get("role") == "user":
                text += " " + entry.get("content", "").lower()
    return any(kw in text for kw in INGREDIENT_QUERY_KEYWORDS)


def should_include_shopping_list(message: str, history: Optional[list] = None) -> bool:
    """Check if shopping list should be loaded based on message content.

    Args:
        message: Current user message.
        history: Optional conversation history to check recent context.

    Returns:
        True if shopping list should be included in context, False otherwise.
    """
    text = message.lower()
    if history:
        for entry in history[-4:]:
            if entry.get("role") == "user":
                text += " " + entry.get("content", "").lower()
    return any(kw in text for kw in SHOPPING_LIST_KEYWORDS)


# ============================================================================
# CONTEXT TEMPLATES
# ============================================================================


def build_user_context_prompt(
    saved_recipes: list[dict],
    meal_plan: list[dict],
    shopping_list: Optional[dict] = None,
    recipe_ingredients: Optional[dict] = None,
) -> str:
    """Build the user context section of the prompt.

    Args:
        saved_recipes: List of {name, category, meal_type, total_time, is_favorite}
        meal_plan: List of {meal_name, main_recipe_name}
        shopping_list: Optional dict with {need: [...], have: [...]}
        recipe_ingredients: Optional dict mapping recipe_name to ingredient list

    Returns:
        Formatted context string to append to system prompt.
    """
    sections = []

    # Saved recipes summary
    if saved_recipes:
        lines = ["📚 HER SAVED RECIPES (Favorites & Recent):"]
        for r in saved_recipes:
            fav = " ⭐" if r.get("is_favorite") else ""
            time_str = f", {r['total_time']}min" if r.get("total_time") else ""
            lines.append(
                f"- {r['name']} ({r['category']}, {r['meal_type']}{time_str}){fav}"
            )
        sections.append("\n".join(lines))

    # Recipe ingredients (when relevant)
    if recipe_ingredients:
        lines = ["🥘 RECIPE INGREDIENTS (for ingredient-based suggestions):"]
        for recipe_name, ingredients in recipe_ingredients.items():
            ing_str = ", ".join(ingredients[:8])  # First 8 to keep it concise
            if len(ingredients) > 8:
                ing_str += f" (+{len(ingredients) - 8} more)"
            lines.append(f"- {recipe_name}: {ing_str}")
        sections.append("\n".join(lines))

    # Current meal plan
    if meal_plan:
        lines = ["📅 CURRENT MEAL PLAN:"]
        for entry in meal_plan:
            lines.append(f"- {entry['meal_name']}: {entry['main_recipe_name']}")
        sections.append("\n".join(lines))

    # Shopping list (only when explicitly referenced)
    if shopping_list:
        lines = ["🛒 SHOPPING LIST:"]
        if shopping_list.get("need"):
            lines.append(f"Need to buy: {', '.join(shopping_list['need'][:15])}")
        if shopping_list.get("have"):
            lines.append(f"Already have: {', '.join(shopping_list['have'][:15])}")
        sections.append("\n".join(lines))

    if not sections:
        return ""

    return "\n\n--- HER DATA ---\n" + "\n\n".join(sections)
