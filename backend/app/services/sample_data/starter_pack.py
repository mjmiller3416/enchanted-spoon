"""app/services/sample_data/starter_pack.py

Curated starter content seeded into every new account so the onboarding tour
has real recipes, meals, a planned week, and a shopping list to point at.

Values use the same slugs the app stores (meal types, recipe categories,
ingredient categories, dietary preferences) and only built-in units, so the
content filters, groups, and converts exactly like user-entered data.

Images: set ``reference_image_path`` / ``banner_image_path`` on a recipe to a
hosted URL (e.g. Cloudinary ``secure_url``) to give it artwork. Recipes left
without one show the standard placeholder. Seeded recipes each get their own
``image_key``, so a user uploading a new image never touches the shared asset.
"""

from typing import Any, Dict, List, Optional, Tuple, TypedDict

# (name, quantity, unit, ingredient_category)
IngredientSpec = Tuple[str, Optional[float], Optional[str], str]


class StarterRecipe(TypedDict, total=False):
    recipe_name: str
    recipe_category: str
    meal_type: str
    diet_pref: Optional[str]
    description: str
    prep_time: int
    cook_time: int
    servings: int
    difficulty: str
    is_favorite: bool
    directions: str
    notes: str
    reference_image_path: Optional[str]
    banner_image_path: Optional[str]
    ingredients: List[IngredientSpec]


class StarterMeal(TypedDict):
    meal_name: str
    main: str
    sides: List[str]
    tags: List[str]
    # Position in the planner, or None to leave it as a saved meal only
    planned: Optional[int]


STARTER_RECIPES: List[StarterRecipe] = [
    # ── Mains ────────────────────────────────────────────────────────────────
    {
        "recipe_name": "Weeknight Beef Tacos",
        "recipe_category": "mexican",
        "meal_type": "dinner",
        "diet_pref": None,
        "description": "Juicy, well-seasoned taco meat with all the fixings, on the table in under 30 minutes.",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "difficulty": "Easy",
        "is_favorite": True,
        "directions": """Heat the olive oil in a large skillet over medium-high heat.
Add the onion and cook until softened, about 4 minutes.
Add the ground beef and cook, breaking it up, until browned, about 6 minutes. Drain excess fat.
Stir in the chili powder, cumin, garlic powder, and salt, then add the tomato sauce and 1/4 cup water.
Simmer until thickened, about 5 minutes.
Warm the tortillas in a dry skillet or wrapped in foil in the oven.
Fill each tortilla with beef and top with lettuce, tomato, cheddar, and sour cream.""",
        "notes": "Swap the beef for ground turkey for a lighter version. Leftover meat makes a great taco salad.",
        "ingredients": [
            ("Ground Beef", 1, "lbs", "meat"),
            ("Yellow Onion", 1, "whole", "produce"),
            ("Olive Oil", 1, "tbs", "oils-and-vinegars"),
            ("Chili Powder", 1, "tbs", "spices"),
            ("Ground Cumin", 2, "tsp", "spices"),
            ("Garlic Powder", 1, "tsp", "spices"),
            ("Salt", 1, "tsp", "spices"),
            ("Tomato Sauce", 8, "oz", "pantry"),
            ("Corn Tortillas", 12, "piece", "bakery"),
            ("Shredded Lettuce", 2, "cup", "produce"),
            ("Roma Tomatoes", 2, "whole", "produce"),
            ("Shredded Cheddar Cheese", 1, "cup", "dairy"),
            ("Sour Cream", 0.5, "cup", "dairy"),
        ],
    },
    {
        "recipe_name": "Creamy Tomato Basil Pasta",
        "recipe_category": "italian",
        "meal_type": "dinner",
        "diet_pref": None,
        "description": "A silky, one-pan tomato cream sauce with fresh basil — pantry staples, restaurant results.",
        "prep_time": 10,
        "cook_time": 20,
        "servings": 4,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Bring a large pot of salted water to a boil and cook the penne until al dente. Reserve 1/2 cup pasta water, then drain.
Meanwhile, melt the butter with the olive oil in a large skillet over medium heat.
Add the garlic and red pepper flakes and cook until fragrant, about 1 minute.
Pour in the crushed tomatoes, season with salt, and simmer for 10 minutes.
Stir in the heavy cream and Parmesan until smooth.
Toss in the pasta, loosening with pasta water as needed.
Tear in the fresh basil and serve with extra Parmesan.""",
        "notes": "Add a handful of baby spinach with the pasta for extra greens.",
        "ingredients": [
            ("Penne Pasta", 1, "lbs", "pantry"),
            ("Crushed Tomatoes", 1, "can", "pantry"),
            ("Heavy Cream", 0.5, "cup", "dairy"),
            ("Parmesan Cheese", 0.75, "cup", "dairy"),
            ("Butter", 2, "tbs", "dairy"),
            ("Olive Oil", 1, "tbs", "oils-and-vinegars"),
            ("Garlic Cloves", 4, None, "produce"),
            ("Red Pepper Flakes", 0.25, "tsp", "spices"),
            ("Fresh Basil", 1, "cup", "produce"),
            ("Salt", 1, "tsp", "spices"),
        ],
    },
    {
        "recipe_name": "Lemon Herb Roast Chicken",
        "recipe_category": "american",
        "meal_type": "dinner",
        "diet_pref": "gluten-free",
        "description": "Crispy-skinned roast chicken perfumed with lemon, garlic, and thyme. A Sunday classic.",
        "prep_time": 15,
        "cook_time": 75,
        "servings": 6,
        "difficulty": "Medium",
        "is_favorite": False,
        "directions": """Preheat the oven to 425°F and pat the chicken completely dry.
Mash the softened butter with the chopped thyme, lemon zest, salt, and pepper.
Loosen the skin over the breast and rub half the butter underneath; rub the rest over the outside.
Stuff the cavity with the halved lemon and the garlic head, halved crosswise.
Roast breast-side up for 70–80 minutes, until the thickest part of the thigh reaches 165°F.
Rest for 15 minutes before carving, spooning the pan juices over the top.""",
        "notes": "Dry-brine overnight (salt, uncovered, in the fridge) for the crispiest skin.",
        "ingredients": [
            ("Whole Chicken", 4, "lbs", "meat"),
            ("Butter", 4, "tbs", "dairy"),
            ("Fresh Thyme", 2, "tbs", "produce"),
            ("Lemon", 1, "whole", "produce"),
            ("Garlic Head", 1, "whole", "produce"),
            ("Salt", 2, "tsp", "spices"),
            ("Black Pepper", 1, "tsp", "spices"),
        ],
    },
    {
        "recipe_name": "Teriyaki Salmon Bowls",
        "recipe_category": "japanese",
        "meal_type": "dinner",
        "diet_pref": "dairy-free",
        "description": "Glazed salmon over rice with crisp cucumber and avocado — fresh, fast, and weeknight-friendly.",
        "prep_time": 15,
        "cook_time": 15,
        "servings": 4,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Cook the rice according to package directions.
Whisk the soy sauce, honey, rice vinegar, and grated ginger together for the glaze.
Season the salmon with salt and sear skin-side up in the sesame oil over medium-high heat for 4 minutes.
Flip, pour in the glaze, and simmer until the salmon is cooked through and glossy, 3–4 minutes.
Divide the rice between bowls and top with salmon, sliced cucumber, avocado, and green onions.
Spoon over any remaining glaze and finish with sesame seeds.""",
        "notes": "Use tamari instead of soy sauce to make this gluten-free.",
        "ingredients": [
            ("Salmon Fillets", 1.5, "lbs", "seafood"),
            ("Jasmine Rice", 1.5, "cup", "pantry"),
            ("Soy Sauce", 0.25, "cup", "condiments"),
            ("Honey", 2, "tbs", "pantry"),
            ("Rice Vinegar", 1, "tbs", "oils-and-vinegars"),
            ("Fresh Ginger", 1, "tbs", "produce"),
            ("Sesame Oil", 1, "tbs", "oils-and-vinegars"),
            ("Cucumber", 1, "whole", "produce"),
            ("Avocado", 1, "whole", "produce"),
            ("Green Onions", 3, "whole", "produce"),
            ("Sesame Seeds", 1, "tbs", "spices"),
        ],
    },
    # ── Sides ────────────────────────────────────────────────────────────────
    {
        "recipe_name": "Cilantro Lime Rice",
        "recipe_category": "mexican",
        "meal_type": "side",
        "diet_pref": "gluten-free",
        "description": "Fluffy rice brightened with lime and fresh cilantro — the perfect partner for tacos.",
        "prep_time": 5,
        "cook_time": 20,
        "servings": 4,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Rinse the rice until the water runs clear.
Melt the butter in a saucepan, add the rice, and toast for 1 minute.
Add the water and salt, bring to a boil, then cover and simmer on low for 18 minutes.
Remove from the heat and let stand, covered, for 5 minutes.
Fluff with a fork and fold in the lime zest, lime juice, and chopped cilantro.""",
        "ingredients": [
            ("Jasmine Rice", 1, "cup", "pantry"),
            ("Butter", 1, "tbs", "dairy"),
            ("Lime", 1, "whole", "produce"),
            ("Fresh Cilantro", 0.5, "cup", "produce"),
            ("Salt", 0.5, "tsp", "spices"),
        ],
    },
    {
        "recipe_name": "Garlic Parmesan Roasted Potatoes",
        "recipe_category": "american",
        "meal_type": "side",
        "diet_pref": "gluten-free",
        "description": "Golden, crispy-edged potatoes tossed with garlic and Parmesan.",
        "prep_time": 10,
        "cook_time": 35,
        "servings": 6,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Preheat the oven to 425°F.
Halve or quarter the potatoes into bite-size pieces.
Toss with olive oil, minced garlic, salt, and pepper and spread on a sheet pan.
Roast for 30–35 minutes, flipping halfway, until golden and crisp.
Toss with Parmesan and chopped parsley straight out of the oven.""",
        "ingredients": [
            ("Baby Potatoes", 2, "lbs", "produce"),
            ("Olive Oil", 3, "tbs", "oils-and-vinegars"),
            ("Garlic Cloves", 4, None, "produce"),
            ("Parmesan Cheese", 0.5, "cup", "dairy"),
            ("Fresh Parsley", 2, "tbs", "produce"),
            ("Salt", 1, "tsp", "spices"),
            ("Black Pepper", 0.5, "tsp", "spices"),
        ],
    },
    {
        "recipe_name": "Simple Green Salad",
        "recipe_category": "mediterranean",
        "meal_type": "side",
        "diet_pref": "vegan",
        "description": "Crisp greens with a bright lemon-Dijon vinaigrette. Goes with everything.",
        "prep_time": 10,
        "cook_time": 0,
        "servings": 4,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Whisk the olive oil, lemon juice, Dijon mustard, maple syrup, salt, and pepper in a large bowl.
Add the mixed greens, sliced cucumber, and halved cherry tomatoes.
Toss gently just before serving.""",
        "ingredients": [
            ("Mixed Greens", 5, "oz", "produce"),
            ("Cucumber", 1, "whole", "produce"),
            ("Cherry Tomatoes", 1, "cup", "produce"),
            ("Olive Oil", 3, "tbs", "oils-and-vinegars"),
            ("Lemon", 1, "whole", "produce"),
            ("Dijon Mustard", 1, "tsp", "condiments"),
            ("Maple Syrup", 1, "tsp", "pantry"),
            ("Salt", 0.5, "tsp", "spices"),
            ("Black Pepper", 0.25, "tsp", "spices"),
        ],
    },
    {
        "recipe_name": "Easy Garlic Bread",
        "recipe_category": "italian",
        "meal_type": "side",
        "diet_pref": None,
        "description": "Buttery, golden garlic bread — made for mopping up pasta sauce.",
        "prep_time": 5,
        "cook_time": 12,
        "servings": 6,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Preheat the oven to 400°F.
Mix the softened butter with the minced garlic, parsley, and salt.
Split the baguette lengthwise and spread the butter evenly over the cut sides.
Bake cut-side up for 10–12 minutes until golden at the edges, then slice and serve.""",
        "ingredients": [
            ("Baguette", 1, "whole", "bakery"),
            ("Butter", 8, "tbs", "dairy"),
            ("Garlic Cloves", 3, None, "produce"),
            ("Fresh Parsley", 1, "tbs", "produce"),
            ("Salt", 0.25, "tsp", "spices"),
        ],
    },
    # ── Breakfast & dessert ─────────────────────────────────────────────────
    {
        "recipe_name": "Fluffy Buttermilk Pancakes",
        "recipe_category": "american",
        "meal_type": "breakfast",
        "diet_pref": None,
        "description": "Tall, tender pancakes for slow weekend mornings.",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "difficulty": "Easy",
        "is_favorite": True,
        "directions": """Whisk the flour, sugar, baking powder, baking soda, and salt in a large bowl.
In another bowl, whisk the buttermilk, eggs, and melted butter.
Pour the wet ingredients into the dry and stir until just combined — a few lumps are fine.
Rest the batter for 5 minutes while a griddle heats over medium.
Pour 1/4 cup batter per pancake and cook until bubbles form, about 2 minutes. Flip and cook 1 minute more.
Serve warm with maple syrup and fresh berries.""",
        "notes": "No buttermilk? Stir 1 tbs lemon juice into 2 cups of milk and let it sit for 5 minutes.",
        "ingredients": [
            ("All-Purpose Flour", 2, "cup", "baking"),
            ("Sugar", 2, "tbs", "baking"),
            ("Baking Powder", 2, "tsp", "baking"),
            ("Baking Soda", 0.5, "tsp", "baking"),
            ("Salt", 0.5, "tsp", "spices"),
            ("Buttermilk", 2, "cup", "dairy"),
            ("Eggs", 2, "whole", "dairy"),
            ("Butter", 3, "tbs", "dairy"),
            ("Maple Syrup", 0.5, "cup", "pantry"),
        ],
    },
    {
        "recipe_name": "Chewy Chocolate Chip Cookies",
        "recipe_category": "american",
        "meal_type": "dessert",
        "diet_pref": None,
        "description": "Crisp edges, chewy centers, and plenty of chocolate.",
        "prep_time": 15,
        "cook_time": 12,
        "servings": 24,
        "difficulty": "Easy",
        "is_favorite": False,
        "directions": """Preheat the oven to 350°F and line two baking sheets with parchment.
Beat the softened butter with the brown and white sugars until light and fluffy, about 3 minutes.
Beat in the eggs and vanilla.
Stir in the flour, baking soda, and salt until just combined, then fold in the chocolate chips.
Scoop 2-tablespoon balls onto the sheets, 2 inches apart.
Bake for 10–12 minutes until the edges are golden but the centers look slightly underdone.
Cool on the sheet for 5 minutes before moving to a rack.""",
        "notes": "Chill the dough for an hour for thicker cookies with deeper flavor.",
        "ingredients": [
            ("Butter", 1, "cup", "dairy"),
            ("Brown Sugar", 1, "cup", "baking"),
            ("Sugar", 0.5, "cup", "baking"),
            ("Eggs", 2, "whole", "dairy"),
            ("Vanilla Extract", 2, "tsp", "baking"),
            ("All-Purpose Flour", 2.25, "cup", "baking"),
            ("Baking Soda", 1, "tsp", "baking"),
            ("Salt", 1, "tsp", "spices"),
            ("Chocolate Chips", 2, "cup", "baking"),
        ],
    },
]


STARTER_MEALS: List[StarterMeal] = [
    {
        "meal_name": "Taco Night",
        "main": "Weeknight Beef Tacos",
        "sides": ["Cilantro Lime Rice"],
        "tags": ["quick", "kid-friendly"],
        "planned": 0,
    },
    {
        "meal_name": "Pasta Night",
        "main": "Creamy Tomato Basil Pasta",
        "sides": ["Easy Garlic Bread", "Simple Green Salad"],
        "tags": ["comfort food"],
        "planned": 1,
    },
    {
        "meal_name": "Sunday Roast",
        "main": "Lemon Herb Roast Chicken",
        "sides": ["Garlic Parmesan Roasted Potatoes", "Simple Green Salad"],
        "tags": ["family", "weekend"],
        "planned": 2,
    },
    {
        "meal_name": "Salmon Bowls",
        "main": "Teriyaki Salmon Bowls",
        "sides": [],
        "tags": ["healthy", "quick"],
        "planned": None,
    },
]


def starter_ingredient_keys() -> set[Tuple[str, str]]:
    """(lowercased name, category) for every ingredient the starter pack creates."""
    return {
        (name.lower(), category)
        for recipe in STARTER_RECIPES
        for name, _qty, _unit, category in recipe["ingredients"]
    }


def starter_image_urls() -> set[str]:
    """Hosted images shared by every account's copy of the starter pack."""
    return {
        url
        for recipe in STARTER_RECIPES
        for url in (recipe.get("reference_image_path"), recipe.get("banner_image_path"))
        if url
    }


def recipe_fields(recipe: StarterRecipe) -> Dict[str, Any]:
    """Recipe-level fields of a starter recipe (everything but ingredients/favorite)."""
    return {k: v for k, v in recipe.items() if k not in ("ingredients", "is_favorite")}
