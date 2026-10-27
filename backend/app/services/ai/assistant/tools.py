"""Gemini function calling tool definitions for the AI assistant.

Defines the tools/functions available to the AI for structured interactions.
"""

from app.services.user_ingredient_category_service import BUILT_IN_INGREDIENT_CATEGORIES

# Store sections Genie may file a shopping item under (every account has these)
SHOPPING_CATEGORIES = [c["value"] for c in BUILT_IN_INGREDIENT_CATEGORIES]

# ============================================================================
# FUNCTION DEFINITIONS FOR GEMINI
# ============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "suggest_recipes",
        "description": "Suggest 4-6 recipe ideas as brief teasers based on the user's request. Use when user asks for ideas, suggestions, dinner options, or 'what can I make with X'. Returns recipe name ideas with brief descriptions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "main_ingredient": {
                    "type": "STRING",
                    "description": "Primary ingredient mentioned (e.g., 'chicken', 'pasta'). Optional.",
                },
                "cuisine_style": {
                    "type": "STRING",
                    "description": "Cuisine or style preference (e.g., 'Italian', 'quick', 'cozy'). Optional.",
                },
                "dietary_restrictions": {
                    "type": "STRING",
                    "description": "Any dietary needs mentioned (e.g., 'vegetarian', 'gluten-free'). Optional.",
                },
                "time_constraint": {
                    "type": "STRING",
                    "description": "Time limit if mentioned (e.g., '30 minutes', 'quick'). Optional.",
                },
                "mood_or_vibe": {
                    "type": "STRING",
                    "description": "Desired vibe (e.g., 'comfort food', 'fancy', 'easy'). Optional.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_recipe",
        "description": "Generate a complete recipe with ingredients and instructions. Use when user selects a specific suggestion OR explicitly asks for a full recipe. Returns structured recipe data.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipe_name": {
                    "type": "STRING",
                    "description": "Name of the recipe to create",
                },
                "style_notes": {
                    "type": "STRING",
                    "description": "Any style/variation notes from the conversation",
                },
                "dietary_restrictions": {
                    "type": "STRING",
                    "description": "Dietary requirements to follow. Default: 'none'",
                },
                "servings": {
                    "type": "INTEGER",
                    "description": "Number of servings. Default: 4",
                },
            },
            "required": ["recipe_name"],
        },
    },
    {
        "name": "answer_cooking_question",
        "description": "Answer a cooking technique question, provide a tip, suggest substitutions, or troubleshoot a problem. Use for general cooking Q&A that doesn't require recipe suggestions or generation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question_type": {
                    "type": "STRING",
                    "enum": [
                        "technique",
                        "substitution",
                        "troubleshooting",
                        "timing",
                        "food_safety",
                        "general",
                    ],
                    "description": "Category of the cooking question",
                },
                "context": {
                    "type": "STRING",
                    "description": "Relevant context from the user's question",
                },
            },
            "required": ["question_type"],
        },
    },
    {
        "name": "add_to_shopping_list",
        "description": "Add one or more items to the user's shopping list. Use ONLY when the user explicitly asks to add, put, or save items to their shopping/grocery list. Items already on the list are skipped automatically. Returns what was actually added.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "description": "The items to add, one entry per distinct item.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {
                                "type": "STRING",
                                "description": "Plain grocery item name in Title Case, without quantity or unit (e.g. 'Ground Beef', 'Milk').",
                            },
                            "quantity": {
                                "type": "NUMBER",
                                "description": "Amount, only if the user gave one. Default: 1",
                            },
                            "unit": {
                                "type": "STRING",
                                "description": "Unit, only if the user gave one (e.g. 'lbs', 'oz', 'can', 'bag').",
                            },
                            "category": {
                                "type": "STRING",
                                "enum": SHOPPING_CATEGORIES,
                                "description": "Store section the item belongs in.",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "add_meals_to_planner",
        "description": "Plan meals from the user's saved recipes and add them to her meal planner. Use ONLY when the user explicitly asks to add, plan, or put meals on her meal planner/menu. Recipes (mains and sides) are picked from her saved library by a dedicated planning step. Returns the meals actually added.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "meal_count": {
                    "type": "INTEGER",
                    "description": "How many meals to add. Default: 1",
                },
                "requirements": {
                    "type": "STRING",
                    "description": "Everything she asked for about these meals, restated completely: proteins or ingredients per meal, cuisines, dish types, specific recipes by name, time limits, things to avoid, and side-dish rules (e.g. '3 with ground beef, 1 with chicken; at least one pasta dish and one Mexican dish; 1-2 side dishes per meal').",
                },
            },
            "required": ["meal_count", "requirements"],
        },
    },
]
