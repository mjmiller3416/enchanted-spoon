#!/usr/bin/env python3
"""
Enchanted Spoon Database Seeder

A comprehensive database seeding utility for the Enchanted Spoon recipe application.
Creates realistic recipes, ingredients, meal selections, and shopping data.

Usage:
    python backend/scripts/seed_database.py --mode replace
    python backend/scripts/seed_database.py --mode append --count 10
    python backend/scripts/seed_database.py --recipes-only --verbose
    python backend/scripts/seed_database.py --clear-only
    python backend/scripts/seed_database.py --help
"""

import argparse
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session


def get_db_and_models():
    """
    Lazy import of database and models to avoid circular import issues.
    Returns a tuple of (SessionLocal, model_classes_dict).
    """
    from app.database.db import SessionLocal
    from app.models import (
        Ingredient,
        Meal,
        PlannerEntry,
        Recipe,
        RecipeIngredient,
        ShoppingItem,
        ShoppingItemContribution,
    )
    return SessionLocal, {
        "Ingredient": Ingredient,
        "Meal": Meal,
        "PlannerEntry": PlannerEntry,
        "Recipe": Recipe,
        "RecipeIngredient": RecipeIngredient,
        "ShoppingItem": ShoppingItem,
        "ShoppingItemContribution": ShoppingItemContribution,
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# INGREDIENT DATA
# ══════════════════════════════════════════════════════════════════════════════════════════════════

INGREDIENTS_BY_CATEGORY: Dict[str, List[str]] = {
    "Produce": [
        "Onion", "Garlic", "Tomatoes", "Bell Pepper", "Jalapeño", "Carrots", "Celery",
        "Potatoes", "Sweet Potato", "Spinach", "Kale", "Lettuce", "Romaine Lettuce",
        "Cucumber", "Zucchini", "Mushrooms", "Broccoli", "Cauliflower", "Green Beans",
        "Asparagus", "Corn", "Avocado", "Lemon", "Lime", "Orange", "Mango", "Cilantro",
        "Parsley", "Basil", "Thyme", "Rosemary", "Ginger", "Scallions", "Shallots",
        "Cherry Tomatoes", "Roma Tomatoes", "Red Onion", "Yellow Onion", "Green Onion",
        "Baby Spinach", "Arugula", "Bean Sprouts", "Bok Choy", "Cabbage", "Red Cabbage",
        "Eggplant", "Fennel", "Leeks", "Radishes", "Snap Peas", "Snow Peas",
    ],
    "Meat & Poultry": [
        "Chicken Breast", "Chicken Thighs", "Ground Beef", "Ground Turkey", "Beef Steak",
        "Pork Tenderloin", "Pork Chops", "Bacon", "Italian Sausage", "Chorizo",
        "Lamb Chops", "Ground Lamb", "Whole Chicken", "Chicken Wings", "Chicken Drumsticks",
        "Beef Chuck Roast", "Beef Sirloin", "Pork Shoulder", "Ham", "Prosciutto",
        "Pancetta", "Turkey Breast", "Duck Breast",
    ],
    "Seafood": [
        "Salmon Fillet", "Shrimp", "Cod Fillet", "Tilapia", "Tuna Steak", "Mahi Mahi",
        "Sea Bass", "Scallops", "Mussels", "Clams", "Crab Meat", "Lobster Tail",
        "Anchovy Fillets", "Calamari", "Halibut",
    ],
    "Dairy & Eggs": [
        "Eggs", "Butter", "Milk", "Heavy Cream", "Sour Cream", "Greek Yogurt",
        "Parmesan Cheese", "Mozzarella Cheese", "Cheddar Cheese", "Feta Cheese",
        "Cream Cheese", "Ricotta Cheese", "Goat Cheese", "Gruyère Cheese",
        "Monterey Jack Cheese", "Provolone Cheese", "Mascarpone", "Crème Fraîche",
        "Half and Half", "Buttermilk", "Cottage Cheese", "Blue Cheese",
    ],
    "Pantry": [
        "Olive Oil", "Vegetable Oil", "Sesame Oil", "Coconut Oil", "Balsamic Vinegar",
        "Red Wine Vinegar", "Apple Cider Vinegar", "Rice Vinegar", "Soy Sauce",
        "Fish Sauce", "Worcestershire Sauce", "Hot Sauce", "Sriracha", "Honey",
        "Maple Syrup", "Brown Sugar", "White Sugar", "All-Purpose Flour",
        "Bread Crumbs", "Panko Bread Crumbs", "Cornstarch", "Baking Powder",
        "Baking Soda", "Chicken Broth", "Beef Broth", "Vegetable Broth",
        "Coconut Milk", "Crushed Tomatoes", "Tomato Paste", "Tomato Sauce",
        "Diced Tomatoes", "Black Beans", "Kidney Beans", "Chickpeas", "Lentils",
        "White Rice", "Brown Rice", "Arborio Rice", "Pasta", "Spaghetti",
        "Penne", "Fettuccine", "Lasagna Noodles", "Rice Noodles", "Peanut Butter",
        "Tahini", "Dijon Mustard", "Yellow Mustard", "Mayonnaise", "Ketchup",
        "BBQ Sauce", "Teriyaki Sauce", "Hoisin Sauce", "Oyster Sauce",
    ],
    "Spices & Seasonings": [
        "Salt", "Black Pepper", "Paprika", "Smoked Paprika", "Cayenne Pepper",
        "Chili Powder", "Cumin", "Coriander", "Turmeric", "Curry Powder",
        "Garam Masala", "Italian Seasoning", "Oregano", "Dried Basil", "Dried Thyme",
        "Bay Leaves", "Cinnamon", "Nutmeg", "Cloves", "Cardamom", "Red Pepper Flakes",
        "Garlic Powder", "Onion Powder", "Dried Rosemary", "Dried Parsley",
        "Chinese Five Spice", "Herbes de Provence", "Taco Seasoning",
    ],
    "Bakery": [
        "Bread", "Baguette", "Ciabatta", "Pita Bread", "Tortillas", "Flour Tortillas",
        "Corn Tortillas", "Hamburger Buns", "Hot Dog Buns", "English Muffins",
        "Croissants", "Naan Bread", "Pizza Dough", "Pie Crust",
    ],
    "Frozen": [
        "Frozen Peas", "Frozen Corn", "Frozen Mixed Vegetables", "Frozen Spinach",
        "Frozen Berries", "Frozen Mango", "Frozen Shrimp", "Ice Cream",
    ],
    "Condiments": [
        "Salsa", "Guacamole", "Pesto", "Marinara Sauce", "Alfredo Sauce",
        "Ranch Dressing", "Caesar Dressing", "Italian Dressing", "Vinaigrette",
        "Hummus", "Tzatziki", "Chimichurri", "Aioli", "Tartar Sauce",
    ],
    "Beverages": [
        "Red Wine", "White Wine", "Beer", "Chicken Stock", "Beef Stock",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RECIPE DATA - 25+ Complete Recipes
# ══════════════════════════════════════════════════════════════════════════════════════════════════

RECIPES_DATA: List[Dict] = [
    # Recipe 1: Classic Spaghetti Bolognese
    {
        "recipe_name": "Classic Spaghetti Bolognese",
        "recipe_category": "Italian",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 75,
        "servings": 6,
        "directions": """Heat olive oil in a large Dutch oven over medium-high heat.
Add the ground beef and Italian sausage, breaking up with a wooden spoon.
Cook until browned, about 8-10 minutes, then drain excess fat.
Add diced onion, carrots, and celery to the pot. Sauté until softened, about 5 minutes.
Stir in minced garlic and cook for another minute until fragrant.
Add tomato paste and stir to coat the meat and vegetables.
Pour in crushed tomatoes, beef broth, and red wine.
Add Italian seasoning, bay leaves, salt, and pepper.
Bring to a boil, then reduce heat and simmer uncovered for 45 minutes to 1 hour.
Meanwhile, cook spaghetti according to package directions until al dente.
Remove bay leaves from sauce and adjust seasoning to taste.
Serve sauce over hot spaghetti and garnish with fresh parsley and Parmesan cheese.""",
        "notes": "For a richer sauce, add a splash of heavy cream at the end. This sauce freezes beautifully for up to 3 months. You can substitute ground turkey for a lighter version.",
        "ingredients": [
            ("Ground Beef", 1, "lb", "Meat & Poultry"),
            ("Italian Sausage", 0.5, "lb", "Meat & Poultry"),
            ("Spaghetti", 1, "lb", "Pantry"),
            ("Crushed Tomatoes", 28, "oz", "Pantry"),
            ("Tomato Paste", 2, "tbsp", "Pantry"),
            ("Beef Broth", 0.5, "cup", "Pantry"),
            ("Red Wine", 0.5, "cup", "Beverages"),
            ("Onion", 1, "whole", "Produce"),
            ("Carrots", 2, "whole", "Produce"),
            ("Celery", 2, "stalks", "Produce"),
            ("Garlic", 4, "cloves", "Produce"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
            ("Italian Seasoning", 1, "tbsp", "Spices & Seasonings"),
            ("Bay Leaves", 2, "whole", "Spices & Seasonings"),
            ("Parmesan Cheese", 0.5, "cup", "Dairy & Eggs"),
        ],
    },

    # Recipe 2: Chicken Tikka Masala
    {
        "recipe_name": "Chicken Tikka Masala",
        "recipe_category": "Indian",
        "meal_type": "Dinner",
        "diet_pref": "Gluten-Free",
        "cook_time": 60,
        "servings": 4,
        "directions": """Cut chicken into 1.5-inch cubes and place in a large bowl.
Mix yogurt, lemon juice, cumin, garam masala, turmeric, and salt for the marinade.
Coat chicken pieces with marinade and refrigerate for at least 30 minutes or overnight.
Preheat oven to 450°F. Thread chicken onto skewers and place on a baking sheet.
Bake for 15-18 minutes until chicken is cooked through and slightly charred.
For the sauce, heat butter in a large pan over medium heat.
Add diced onion and cook until softened and golden, about 8 minutes.
Add garlic and ginger, cooking for another minute.
Stir in tomato paste, garam masala, cumin, paprika, and cayenne.
Pour in crushed tomatoes and simmer for 10 minutes.
Add heavy cream and stir to combine, then add the cooked chicken.
Simmer together for 5-10 minutes until sauce thickens.
Garnish with fresh cilantro and serve over basmati rice or with naan bread.""",
        "notes": "The longer you marinate the chicken, the more flavorful it will be. For extra heat, add more cayenne pepper. This dish pairs perfectly with garlic naan and cucumber raita.",
        "ingredients": [
            ("Chicken Breast", 1.5, "lbs", "Meat & Poultry"),
            ("Greek Yogurt", 0.75, "cup", "Dairy & Eggs"),
            ("Lemon", 1, "whole", "Produce"),
            ("Heavy Cream", 1, "cup", "Dairy & Eggs"),
            ("Crushed Tomatoes", 14, "oz", "Pantry"),
            ("Tomato Paste", 2, "tbsp", "Pantry"),
            ("Butter", 3, "tbsp", "Dairy & Eggs"),
            ("Onion", 1, "large", "Produce"),
            ("Garlic", 4, "cloves", "Produce"),
            ("Ginger", 1, "inch", "Produce"),
            ("Garam Masala", 2, "tbsp", "Spices & Seasonings"),
            ("Cumin", 1, "tsp", "Spices & Seasonings"),
            ("Turmeric", 0.5, "tsp", "Spices & Seasonings"),
            ("Paprika", 1, "tsp", "Spices & Seasonings"),
            ("Cayenne Pepper", 0.25, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 3: Beef Tacos with Fresh Salsa
    {
        "recipe_name": "Beef Tacos with Fresh Salsa",
        "recipe_category": "Mexican",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 35,
        "servings": 4,
        "directions": """Start by making the fresh salsa: dice tomatoes, onion, and jalapeño.
Combine with chopped cilantro, lime juice, and salt. Set aside.
Heat oil in a large skillet over medium-high heat.
Add ground beef and cook, breaking it apart, until browned.
Drain excess fat if needed.
Add taco seasoning and water according to package directions.
Simmer for 5 minutes until sauce thickens.
Warm taco shells according to package directions.
Set up a taco bar with seasoned beef, fresh salsa, and toppings.
Top tacos with shredded cheese, lettuce, sour cream, and salsa.
Serve immediately with lime wedges on the side.""",
        "notes": "For crispier shells, brush with oil and bake at 375°F for 3-4 minutes. You can also use soft flour tortillas for a different experience.",
        "ingredients": [
            ("Ground Beef", 1, "lb", "Meat & Poultry"),
            ("Taco Seasoning", 1, "packet", "Spices & Seasonings"),
            ("Corn Tortillas", 12, "whole", "Bakery"),
            ("Tomatoes", 3, "whole", "Produce"),
            ("Red Onion", 0.5, "whole", "Produce"),
            ("Jalapeño", 1, "whole", "Produce"),
            ("Cilantro", 0.25, "cup", "Produce"),
            ("Lime", 2, "whole", "Produce"),
            ("Cheddar Cheese", 1, "cup", "Dairy & Eggs"),
            ("Lettuce", 2, "cups", "Produce"),
            ("Sour Cream", 0.5, "cup", "Dairy & Eggs"),
            ("Vegetable Oil", 1, "tbsp", "Pantry"),
        ],
    },

    # Recipe 4: Vegetable Stir Fry with Tofu
    {
        "recipe_name": "Vegetable Stir Fry with Tofu",
        "recipe_category": "Asian",
        "meal_type": "Dinner",
        "diet_pref": "Vegan",
        "cook_time": 30,
        "servings": 4,
        "directions": """Press tofu for 15 minutes to remove excess moisture.
Cut tofu into 1-inch cubes and season with salt.
Heat sesame oil in a wok or large skillet over high heat.
Add tofu and cook until golden on all sides, about 5-6 minutes. Remove and set aside.
Add more oil to the wok if needed.
Add broccoli and cook for 2 minutes.
Add bell peppers, snap peas, and carrots. Stir fry for 3-4 minutes.
Add garlic, ginger, and mushrooms. Cook for another 2 minutes.
Mix together soy sauce, rice vinegar, sesame oil, and cornstarch slurry.
Pour sauce over vegetables and add tofu back to the wok.
Toss everything together until sauce thickens and coats the vegetables.
Garnish with sesame seeds and green onions.
Serve over steamed rice or noodles.""",
        "notes": "For best results, make sure your wok is very hot before adding ingredients. Cut all vegetables the same size for even cooking.",
        "ingredients": [
            ("Tofu", 14, "oz", "Pantry"),
            ("Broccoli", 2, "cups", "Produce"),
            ("Bell Pepper", 2, "whole", "Produce"),
            ("Snap Peas", 1, "cup", "Produce"),
            ("Carrots", 2, "whole", "Produce"),
            ("Mushrooms", 8, "oz", "Produce"),
            ("Garlic", 3, "cloves", "Produce"),
            ("Ginger", 1, "tbsp", "Produce"),
            ("Soy Sauce", 3, "tbsp", "Pantry"),
            ("Rice Vinegar", 1, "tbsp", "Pantry"),
            ("Sesame Oil", 2, "tbsp", "Pantry"),
            ("Cornstarch", 1, "tbsp", "Pantry"),
            ("Green Onion", 3, "stalks", "Produce"),
            ("White Rice", 2, "cups", "Pantry"),
        ],
    },

    # Recipe 5: Greek Salad with Grilled Chicken
    {
        "recipe_name": "Greek Salad with Grilled Chicken",
        "recipe_category": "Mediterranean",
        "meal_type": "Lunch",
        "diet_pref": "Gluten-Free",
        "cook_time": 25,
        "servings": 4,
        "directions": """Season chicken breasts with olive oil, oregano, garlic powder, salt, and pepper.
Preheat grill or grill pan to medium-high heat.
Grill chicken for 6-7 minutes per side until internal temperature reaches 165°F.
Let chicken rest for 5 minutes, then slice into strips.
Prepare the dressing by whisking olive oil, red wine vinegar, lemon juice, oregano, and garlic.
In a large bowl, combine chopped romaine, cucumber, tomatoes, red onion, and olives.
Toss salad with dressing.
Top with sliced grilled chicken and crumbled feta cheese.
Garnish with fresh oregano and serve immediately.""",
        "notes": "You can marinate the chicken for up to 24 hours for more flavor. Add chickpeas for extra protein.",
        "ingredients": [
            ("Chicken Breast", 1.5, "lbs", "Meat & Poultry"),
            ("Romaine Lettuce", 2, "heads", "Produce"),
            ("Cucumber", 1, "whole", "Produce"),
            ("Cherry Tomatoes", 1, "pint", "Produce"),
            ("Red Onion", 0.5, "whole", "Produce"),
            ("Kalamata Olives", 0.5, "cup", "Pantry"),
            ("Feta Cheese", 6, "oz", "Dairy & Eggs"),
            ("Olive Oil", 0.25, "cup", "Pantry"),
            ("Red Wine Vinegar", 2, "tbsp", "Pantry"),
            ("Lemon", 1, "whole", "Produce"),
            ("Oregano", 1, "tsp", "Spices & Seasonings"),
            ("Garlic Powder", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 6: Mushroom Risotto
    {
        "recipe_name": "Mushroom Risotto",
        "recipe_category": "Italian",
        "meal_type": "Dinner",
        "diet_pref": "Vegetarian",
        "cook_time": 45,
        "servings": 4,
        "directions": """Keep vegetable broth warm in a saucepan over low heat.
Heat olive oil in a large heavy-bottomed pan over medium heat.
Add sliced mushrooms and cook until golden brown, about 8 minutes. Set aside.
In the same pan, melt butter and sauté shallots until translucent.
Add arborio rice and toast for 2 minutes, stirring constantly.
Pour in white wine and stir until absorbed.
Begin adding warm broth one ladle at a time, stirring frequently.
Wait until each addition is absorbed before adding more.
Continue for about 18-20 minutes until rice is creamy but still al dente.
Stir in cooked mushrooms, remaining butter, and Parmesan cheese.
Season with salt and pepper to taste.
Garnish with fresh thyme and additional Parmesan.
Serve immediately while hot and creamy.""",
        "notes": "The key to perfect risotto is patience - keep stirring and add broth gradually. Use a mix of wild mushrooms for deeper flavor.",
        "ingredients": [
            ("Arborio Rice", 1.5, "cups", "Pantry"),
            ("Mushrooms", 12, "oz", "Produce"),
            ("Vegetable Broth", 6, "cups", "Pantry"),
            ("White Wine", 0.5, "cup", "Beverages"),
            ("Shallots", 2, "whole", "Produce"),
            ("Butter", 4, "tbsp", "Dairy & Eggs"),
            ("Parmesan Cheese", 0.75, "cup", "Dairy & Eggs"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
            ("Thyme", 4, "sprigs", "Produce"),
            ("Garlic", 2, "cloves", "Produce"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 7: BBQ Pulled Pork Sandwiches
    {
        "recipe_name": "BBQ Pulled Pork Sandwiches",
        "recipe_category": "American",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 480,
        "servings": 10,
        "directions": """Combine brown sugar, paprika, garlic powder, onion powder, cumin, salt, and pepper for the rub.
Pat pork shoulder dry and coat generously with the spice rub on all sides.
Place sliced onions in the bottom of a slow cooker.
Set the pork shoulder on top of the onions, fat side up.
Add apple cider vinegar around the meat (not on top to preserve the rub).
Cover and cook on low for 8-10 hours or high for 5-6 hours.
Pork is done when it reaches 200°F and shreds easily.
Remove pork and let rest for 10 minutes.
Shred the meat using two forks, discarding any large fat pieces.
Return shredded pork to the slow cooker with cooking juices.
Add BBQ sauce and toss to coat.
Toast hamburger buns lightly.
Pile pulled pork onto buns and top with coleslaw if desired.
Serve with extra BBQ sauce on the side.""",
        "notes": "Let the pork rest in the juices for 10-15 minutes before serving for maximum moisture. Leftovers make excellent nachos or tacos.",
        "ingredients": [
            ("Pork Shoulder", 4, "lbs", "Meat & Poultry"),
            ("BBQ Sauce", 2, "cups", "Pantry"),
            ("Brown Sugar", 0.25, "cup", "Pantry"),
            ("Paprika", 2, "tbsp", "Spices & Seasonings"),
            ("Garlic Powder", 1, "tbsp", "Spices & Seasonings"),
            ("Onion Powder", 1, "tbsp", "Spices & Seasonings"),
            ("Cumin", 1, "tsp", "Spices & Seasonings"),
            ("Onion", 2, "whole", "Produce"),
            ("Apple Cider Vinegar", 0.5, "cup", "Pantry"),
            ("Hamburger Buns", 10, "whole", "Bakery"),
            ("Salt", 2, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 1, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 8: Thai Green Curry
    {
        "recipe_name": "Thai Green Curry",
        "recipe_category": "Asian",
        "meal_type": "Dinner",
        "diet_pref": "Gluten-Free",
        "cook_time": 35,
        "servings": 4,
        "directions": """Slice chicken into thin strips.
Heat coconut oil in a large wok or deep pan over medium-high heat.
Add green curry paste and fry for 1-2 minutes until fragrant.
Pour in half the coconut milk and stir to combine with paste.
Add chicken strips and cook for 5 minutes, stirring occasionally.
Add remaining coconut milk, chicken broth, and fish sauce.
Add eggplant, bamboo shoots, and bell peppers.
Simmer for 10-15 minutes until vegetables are tender and chicken is cooked through.
Add Thai basil leaves in the last minute of cooking.
Taste and adjust with more fish sauce or sugar as needed.
Serve over jasmine rice with lime wedges and fresh Thai basil.""",
        "notes": "Adjust the amount of curry paste based on your heat preference. You can substitute tofu for chicken for a vegetarian version.",
        "ingredients": [
            ("Chicken Thighs", 1.5, "lbs", "Meat & Poultry"),
            ("Coconut Milk", 2, "cans", "Pantry"),
            ("Green Curry Paste", 3, "tbsp", "Pantry"),
            ("Chicken Broth", 0.5, "cup", "Pantry"),
            ("Fish Sauce", 2, "tbsp", "Pantry"),
            ("Eggplant", 1, "whole", "Produce"),
            ("Bell Pepper", 1, "whole", "Produce"),
            ("Bamboo Shoots", 1, "can", "Pantry"),
            ("Basil", 1, "cup", "Produce"),
            ("Coconut Oil", 2, "tbsp", "Pantry"),
            ("White Sugar", 1, "tsp", "Pantry"),
            ("Lime", 1, "whole", "Produce"),
            ("White Rice", 2, "cups", "Pantry"),
        ],
    },

    # Recipe 9: Classic Caesar Salad
    {
        "recipe_name": "Classic Caesar Salad",
        "recipe_category": "American",
        "meal_type": "Lunch",
        "diet_pref": None,
        "cook_time": 20,
        "servings": 4,
        "directions": """For homemade croutons: cube bread, toss with olive oil, garlic, and salt.
Bake at 375°F for 10-12 minutes until golden and crispy.
For the dressing: mince garlic and anchovy fillets into a paste.
In a bowl, whisk together garlic-anchovy paste, egg yolk, Dijon mustard, and lemon juice.
Slowly drizzle in olive oil while whisking to emulsify.
Stir in grated Parmesan cheese.
Season with Worcestershire sauce, salt, and pepper.
Wash and dry romaine lettuce, then tear into bite-sized pieces.
Place lettuce in a large bowl and toss with dressing to coat.
Add croutons and toss gently.
Top with shaved Parmesan cheese and cracked black pepper.
Serve immediately as a side or add grilled chicken for a main course.""",
        "notes": "For a safer version, use pasteurized eggs or mayonnaise as a base. Add grilled chicken or shrimp for a complete meal.",
        "ingredients": [
            ("Romaine Lettuce", 2, "heads", "Produce"),
            ("Parmesan Cheese", 0.75, "cup", "Dairy & Eggs"),
            ("Bread", 4, "slices", "Bakery"),
            ("Anchovy Fillets", 4, "fillets", "Seafood"),
            ("Eggs", 1, "whole", "Dairy & Eggs"),
            ("Garlic", 2, "cloves", "Produce"),
            ("Lemon", 1, "whole", "Produce"),
            ("Olive Oil", 0.5, "cup", "Pantry"),
            ("Dijon Mustard", 1, "tsp", "Pantry"),
            ("Worcestershire Sauce", 1, "tsp", "Pantry"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 10: Homemade Margherita Pizza
    {
        "recipe_name": "Homemade Margherita Pizza",
        "recipe_category": "Italian",
        "meal_type": "Dinner",
        "diet_pref": "Vegetarian",
        "cook_time": 90,
        "servings": 4,
        "directions": """For the dough: combine warm water, yeast, and sugar. Let stand for 5 minutes until foamy.
Add flour, olive oil, and salt. Knead for 8-10 minutes until smooth and elastic.
Place in an oiled bowl, cover, and let rise for 1 hour until doubled.
Preheat oven to 475°F with a pizza stone if available.
For the sauce: blend San Marzano tomatoes with garlic, olive oil, salt, and basil.
Punch down dough and stretch into a 12-inch circle on a floured surface.
Transfer to a pizza peel or baking sheet dusted with cornmeal.
Spread a thin layer of sauce, leaving a 1-inch border.
Add torn fresh mozzarella pieces evenly over sauce.
Drizzle with olive oil.
Bake for 10-15 minutes until crust is golden and cheese is bubbly.
Remove from oven and immediately top with fresh basil leaves.
Let cool slightly, slice, and serve.""",
        "notes": "For extra crispness, par-bake the crust for 5 minutes before adding toppings. San Marzano tomatoes make the best sauce.",
        "ingredients": [
            ("All-Purpose Flour", 3, "cups", "Pantry"),
            ("Active Dry Yeast", 1, "packet", "Pantry"),
            ("Mozzarella Cheese", 8, "oz", "Dairy & Eggs"),
            ("San Marzano Tomatoes", 14, "oz", "Pantry"),
            ("Basil", 0.5, "cup", "Produce"),
            ("Olive Oil", 3, "tbsp", "Pantry"),
            ("Garlic", 2, "cloves", "Produce"),
            ("White Sugar", 1, "tsp", "Pantry"),
            ("Salt", 1.5, "tsp", "Spices & Seasonings"),
            ("Cornmeal", 2, "tbsp", "Pantry"),
        ],
    },

    # Recipe 11: Beef Stroganoff
    {
        "recipe_name": "Beef Stroganoff",
        "recipe_category": "Comfort Food",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 40,
        "servings": 6,
        "directions": """Slice beef sirloin into thin strips against the grain.
Season beef with salt and pepper.
Heat oil in a large skillet over high heat.
Sear beef in batches until browned but not cooked through, about 1-2 minutes per side. Set aside.
Reduce heat to medium and add butter to the skillet.
Sauté sliced onions until softened, about 5 minutes.
Add mushrooms and cook until golden and liquid evaporates, about 8 minutes.
Add minced garlic and cook for 1 minute.
Sprinkle flour over vegetables and stir for 1 minute.
Pour in beef broth and Worcestershire sauce, stirring to deglaze the pan.
Simmer until sauce thickens, about 3-4 minutes.
Reduce heat to low and stir in sour cream.
Return beef to the pan and cook until just heated through.
Season with salt and pepper to taste.
Serve over egg noodles or mashed potatoes, garnished with fresh parsley.""",
        "notes": "Don't boil the sauce after adding sour cream or it will curdle. Use a good quality beef for the best results.",
        "ingredients": [
            ("Beef Sirloin", 1.5, "lbs", "Meat & Poultry"),
            ("Egg Noodles", 12, "oz", "Pantry"),
            ("Mushrooms", 12, "oz", "Produce"),
            ("Onion", 1, "large", "Produce"),
            ("Garlic", 3, "cloves", "Produce"),
            ("Beef Broth", 1.5, "cups", "Pantry"),
            ("Sour Cream", 1, "cup", "Dairy & Eggs"),
            ("Butter", 3, "tbsp", "Dairy & Eggs"),
            ("All-Purpose Flour", 2, "tbsp", "Pantry"),
            ("Worcestershire Sauce", 1, "tbsp", "Pantry"),
            ("Vegetable Oil", 2, "tbsp", "Pantry"),
            ("Parsley", 0.25, "cup", "Produce"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 12: Shrimp Scampi
    {
        "recipe_name": "Shrimp Scampi",
        "recipe_category": "Italian",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 25,
        "servings": 4,
        "directions": """Cook linguine according to package directions until al dente. Reserve 1 cup pasta water.
Meanwhile, season shrimp with salt and pepper.
Heat olive oil and half the butter in a large skillet over medium-high heat.
Add shrimp in a single layer and cook for 1-2 minutes per side until pink. Remove and set aside.
Reduce heat to medium and add remaining butter.
Sauté minced garlic for 30 seconds until fragrant.
Add white wine and lemon juice, scraping up any browned bits.
Simmer for 2-3 minutes until slightly reduced.
Return shrimp to the pan and add red pepper flakes.
Toss in cooked pasta with a splash of pasta water if needed.
Add fresh parsley and toss to combine.
Serve immediately with crusty bread to soak up the sauce.""",
        "notes": "Don't overcook the shrimp - they should just turn pink. The pasta water helps create a silky sauce that coats the noodles.",
        "ingredients": [
            ("Shrimp", 1.5, "lbs", "Seafood"),
            ("Linguine", 1, "lb", "Pantry"),
            ("Butter", 6, "tbsp", "Dairy & Eggs"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
            ("Garlic", 6, "cloves", "Produce"),
            ("White Wine", 0.75, "cup", "Beverages"),
            ("Lemon", 2, "whole", "Produce"),
            ("Red Pepper Flakes", 0.25, "tsp", "Spices & Seasonings"),
            ("Parsley", 0.5, "cup", "Produce"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 13: Vegetarian Chili
    {
        "recipe_name": "Vegetarian Chili",
        "recipe_category": "Comfort Food",
        "meal_type": "Dinner",
        "diet_pref": "Vegan",
        "cook_time": 50,
        "servings": 8,
        "directions": """Heat oil in a large Dutch oven over medium heat.
Add diced onion, bell peppers, and jalapeño. Sauté until softened, about 5-7 minutes.
Add minced garlic and cook for another minute.
Stir in chili powder, cumin, smoked paprika, oregano, and cayenne.
Toast spices for 1 minute until fragrant.
Add diced tomatoes, crushed tomatoes, and vegetable broth.
Drain and rinse all beans, then add to the pot.
Add corn and stir everything to combine.
Bring to a boil, then reduce heat and simmer for 30-40 minutes.
Season with salt and pepper to taste.
For thicker chili, mash some beans against the side of the pot.
Serve in bowls topped with avocado, sour cream, cilantro, and shredded cheese.
Enjoy with cornbread on the side.""",
        "notes": "This chili tastes even better the next day after the flavors meld. Add a tablespoon of cocoa powder for depth.",
        "ingredients": [
            ("Black Beans", 2, "cans", "Pantry"),
            ("Kidney Beans", 1, "can", "Pantry"),
            ("Diced Tomatoes", 28, "oz", "Pantry"),
            ("Crushed Tomatoes", 14, "oz", "Pantry"),
            ("Vegetable Broth", 1, "cup", "Pantry"),
            ("Corn", 1.5, "cups", "Produce"),
            ("Onion", 1, "large", "Produce"),
            ("Bell Pepper", 2, "whole", "Produce"),
            ("Jalapeño", 1, "whole", "Produce"),
            ("Garlic", 4, "cloves", "Produce"),
            ("Chili Powder", 3, "tbsp", "Spices & Seasonings"),
            ("Cumin", 2, "tsp", "Spices & Seasonings"),
            ("Smoked Paprika", 1, "tsp", "Spices & Seasonings"),
            ("Oregano", 1, "tsp", "Spices & Seasonings"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
        ],
    },

    # Recipe 14: Lemon Herb Roasted Chicken
    {
        "recipe_name": "Lemon Herb Roasted Chicken",
        "recipe_category": "Comfort Food",
        "meal_type": "Dinner",
        "diet_pref": "Gluten-Free",
        "cook_time": 90,
        "servings": 6,
        "directions": """Remove chicken from refrigerator 30 minutes before cooking.
Preheat oven to 425°F.
Pat chicken dry inside and out with paper towels.
Mix softened butter with minced garlic, lemon zest, and chopped herbs.
Carefully loosen skin from the breast meat without tearing.
Spread herb butter under the skin and over the entire bird.
Season inside and out generously with salt and pepper.
Place halved lemon and remaining herbs inside the cavity.
Tie legs together with kitchen twine.
Place chicken breast-side up on a rack in a roasting pan.
Roast for 1 hour to 1 hour 15 minutes until juices run clear and thigh reaches 165°F.
Let rest for 15 minutes before carving.
Serve with pan drippings as a simple sauce.""",
        "notes": "Letting the chicken come to room temperature before roasting ensures even cooking. Save the carcass to make homemade chicken stock.",
        "ingredients": [
            ("Whole Chicken", 4, "lbs", "Meat & Poultry"),
            ("Butter", 4, "tbsp", "Dairy & Eggs"),
            ("Lemon", 2, "whole", "Produce"),
            ("Garlic", 6, "cloves", "Produce"),
            ("Rosemary", 4, "sprigs", "Produce"),
            ("Thyme", 6, "sprigs", "Produce"),
            ("Parsley", 0.25, "cup", "Produce"),
            ("Salt", 1, "tbsp", "Spices & Seasonings"),
            ("Black Pepper", 1, "tsp", "Spices & Seasonings"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
        ],
    },

    # Recipe 15: Fish Tacos with Mango Salsa
    {
        "recipe_name": "Fish Tacos with Mango Salsa",
        "recipe_category": "Mexican",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 30,
        "servings": 4,
        "directions": """Prepare mango salsa: dice mango, red onion, jalapeño, and cilantro.
Combine with lime juice and salt. Refrigerate while preparing fish.
Make the chipotle crema: mix sour cream, chipotle peppers, lime juice, and salt.
Season fish fillets with cumin, paprika, garlic powder, salt, and pepper.
Heat oil in a large skillet over medium-high heat.
Cook fish for 3-4 minutes per side until opaque and flakes easily.
Break fish into large chunks.
Warm corn tortillas on a dry skillet or directly over a gas flame.
Assemble tacos: place fish chunks on tortillas.
Top with shredded cabbage, mango salsa, and chipotle crema.
Garnish with extra cilantro and lime wedges.
Serve immediately.""",
        "notes": "Mahi mahi, cod, or tilapia all work great for fish tacos. For crispier fish, dust with cornstarch before cooking.",
        "ingredients": [
            ("Mahi Mahi", 1.5, "lbs", "Seafood"),
            ("Corn Tortillas", 12, "whole", "Bakery"),
            ("Mango", 2, "whole", "Produce"),
            ("Red Onion", 0.5, "whole", "Produce"),
            ("Jalapeño", 1, "whole", "Produce"),
            ("Cilantro", 0.5, "cup", "Produce"),
            ("Lime", 3, "whole", "Produce"),
            ("Cabbage", 2, "cups", "Produce"),
            ("Sour Cream", 0.5, "cup", "Dairy & Eggs"),
            ("Chipotle Peppers", 2, "peppers", "Pantry"),
            ("Cumin", 1, "tsp", "Spices & Seasonings"),
            ("Paprika", 1, "tsp", "Spices & Seasonings"),
            ("Garlic Powder", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 16: Creamy Tomato Soup
    {
        "recipe_name": "Creamy Tomato Soup",
        "recipe_category": "Comfort Food",
        "meal_type": "Lunch",
        "diet_pref": "Vegetarian",
        "cook_time": 45,
        "servings": 6,
        "directions": """Preheat oven to 400°F.
Cut Roma tomatoes in half and place on a baking sheet.
Drizzle with olive oil, season with salt and pepper, and add whole garlic cloves.
Roast for 25-30 minutes until tomatoes are caramelized and soft.
In a large pot, melt butter over medium heat.
Sauté diced onion and carrots until softened, about 8 minutes.
Add roasted tomatoes and garlic to the pot.
Pour in vegetable broth and canned tomatoes.
Add tomato paste, sugar, and Italian seasoning.
Bring to a simmer and cook for 10 minutes.
Use an immersion blender to puree until smooth.
Stir in heavy cream and basil.
Adjust seasoning to taste.
Serve hot with a swirl of cream and fresh basil.
Pair with grilled cheese sandwiches for a classic combo.""",
        "notes": "Roasting the tomatoes adds incredible depth of flavor. For a lighter version, use half-and-half instead of heavy cream.",
        "ingredients": [
            ("Roma Tomatoes", 2, "lbs", "Produce"),
            ("Diced Tomatoes", 14, "oz", "Pantry"),
            ("Tomato Paste", 2, "tbsp", "Pantry"),
            ("Vegetable Broth", 3, "cups", "Pantry"),
            ("Heavy Cream", 0.5, "cup", "Dairy & Eggs"),
            ("Butter", 2, "tbsp", "Dairy & Eggs"),
            ("Onion", 1, "whole", "Produce"),
            ("Carrots", 1, "whole", "Produce"),
            ("Garlic", 4, "cloves", "Produce"),
            ("Basil", 0.25, "cup", "Produce"),
            ("Italian Seasoning", 1, "tsp", "Spices & Seasonings"),
            ("White Sugar", 1, "tsp", "Pantry"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
        ],
    },

    # Recipe 17: Pad Thai
    {
        "recipe_name": "Pad Thai",
        "recipe_category": "Asian",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 35,
        "servings": 4,
        "directions": """Soak rice noodles in warm water for 30 minutes until pliable but not soft. Drain.
Mix the sauce: combine tamarind paste, fish sauce, brown sugar, and rice vinegar.
Heat oil in a wok over high heat.
Add shrimp and cook for 2 minutes until pink. Remove and set aside.
Add more oil if needed. Cook beaten eggs, scrambling lightly, then push to the side.
Add drained noodles to the wok.
Pour sauce over noodles and toss to coat evenly.
Cook for 2-3 minutes until noodles are tender.
Add shrimp back to the wok along with bean sprouts and scallions.
Toss everything together for 1 minute.
Remove from heat and add half the peanuts.
Serve immediately topped with remaining peanuts, cilantro, and lime wedges.
Offer extra fish sauce and chili flakes on the side.""",
        "notes": "The key is to have all ingredients prepped before you start cooking - it goes fast! For vegetarian, substitute tofu for shrimp and use soy sauce instead of fish sauce.",
        "ingredients": [
            ("Rice Noodles", 8, "oz", "Pantry"),
            ("Shrimp", 12, "oz", "Seafood"),
            ("Eggs", 2, "whole", "Dairy & Eggs"),
            ("Tamarind Paste", 3, "tbsp", "Pantry"),
            ("Fish Sauce", 3, "tbsp", "Pantry"),
            ("Brown Sugar", 2, "tbsp", "Pantry"),
            ("Rice Vinegar", 1, "tbsp", "Pantry"),
            ("Bean Sprouts", 2, "cups", "Produce"),
            ("Scallions", 4, "stalks", "Produce"),
            ("Peanuts", 0.5, "cup", "Pantry"),
            ("Cilantro", 0.25, "cup", "Produce"),
            ("Lime", 1, "whole", "Produce"),
            ("Vegetable Oil", 3, "tbsp", "Pantry"),
            ("Garlic", 3, "cloves", "Produce"),
        ],
    },

    # Recipe 18: Shepherd's Pie
    {
        "recipe_name": "Shepherd's Pie",
        "recipe_category": "Comfort Food",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 75,
        "servings": 8,
        "directions": """Peel and cube potatoes. Boil in salted water until tender, about 15-20 minutes.
Drain and mash with butter, milk, and salt until smooth. Set aside.
Preheat oven to 400°F.
In a large skillet, brown ground lamb (or beef) over medium-high heat.
Add diced onion, carrots, and celery. Cook until softened, about 5-7 minutes.
Stir in minced garlic and tomato paste.
Add flour and stir for 1 minute.
Pour in beef broth and Worcestershire sauce.
Add peas, corn, and thyme. Season with salt and pepper.
Simmer until sauce thickens, about 8-10 minutes.
Transfer meat mixture to a 9x13 baking dish.
Spread mashed potatoes evenly over the top.
Create peaks with a fork for crispy edges.
Bake for 25-30 minutes until golden and bubbling.
Let rest 10 minutes before serving.""",
        "notes": "Traditional shepherd's pie uses lamb; cottage pie uses beef. For extra crispy top, broil for the last 2-3 minutes.",
        "ingredients": [
            ("Ground Lamb", 2, "lbs", "Meat & Poultry"),
            ("Potatoes", 2.5, "lbs", "Produce"),
            ("Butter", 4, "tbsp", "Dairy & Eggs"),
            ("Milk", 0.5, "cup", "Dairy & Eggs"),
            ("Onion", 1, "whole", "Produce"),
            ("Carrots", 2, "whole", "Produce"),
            ("Celery", 2, "stalks", "Produce"),
            ("Garlic", 3, "cloves", "Produce"),
            ("Beef Broth", 1, "cup", "Pantry"),
            ("Worcestershire Sauce", 2, "tbsp", "Pantry"),
            ("Tomato Paste", 2, "tbsp", "Pantry"),
            ("Frozen Peas", 1, "cup", "Frozen"),
            ("Corn", 0.5, "cup", "Produce"),
            ("All-Purpose Flour", 2, "tbsp", "Pantry"),
            ("Thyme", 1, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 19: Caprese Salad
    {
        "recipe_name": "Caprese Salad",
        "recipe_category": "Italian",
        "meal_type": "Side Dish",
        "diet_pref": "Vegetarian",
        "cook_time": 10,
        "servings": 4,
        "directions": """Select ripe, flavorful tomatoes - heirloom varieties work beautifully.
Slice tomatoes into 1/4-inch thick rounds.
Slice fresh mozzarella into similar thickness.
Arrange alternating slices of tomato and mozzarella on a serving platter.
Tuck fresh basil leaves between the slices.
Drizzle generously with extra virgin olive oil.
Add a drizzle of balsamic glaze in a zigzag pattern.
Season with flaky sea salt and freshly cracked black pepper.
Let sit for 5 minutes to allow flavors to meld.
Serve at room temperature for best flavor.""",
        "notes": "Use the best quality ingredients you can find - this simple dish relies on them. Let the mozzarella come to room temperature before serving.",
        "ingredients": [
            ("Tomatoes", 4, "whole", "Produce"),
            ("Mozzarella Cheese", 16, "oz", "Dairy & Eggs"),
            ("Basil", 1, "bunch", "Produce"),
            ("Olive Oil", 3, "tbsp", "Pantry"),
            ("Balsamic Vinegar", 2, "tbsp", "Pantry"),
            ("Salt", 0.5, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.25, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 20: Honey Garlic Salmon
    {
        "recipe_name": "Honey Garlic Salmon",
        "recipe_category": "Healthy",
        "meal_type": "Dinner",
        "diet_pref": "Gluten-Free",
        "cook_time": 25,
        "servings": 4,
        "directions": """Pat salmon fillets dry and season with salt and pepper.
In a small bowl, whisk together honey, soy sauce, minced garlic, and lemon juice.
Heat olive oil in an oven-safe skillet over medium-high heat.
Place salmon skin-side up and sear for 3-4 minutes until golden.
Flip salmon so skin-side is down.
Pour honey garlic sauce around the salmon.
Transfer skillet to 400°F oven.
Bake for 8-10 minutes until salmon flakes easily and reaches 145°F.
Spoon sauce from pan over salmon.
Garnish with sesame seeds and sliced green onions.
Serve immediately over rice or with steamed vegetables.""",
        "notes": "Don't overcook the salmon - it should be slightly translucent in the center. For a crispier skin, start skin-side down instead.",
        "ingredients": [
            ("Salmon Fillet", 4, "fillets", "Seafood"),
            ("Honey", 3, "tbsp", "Pantry"),
            ("Soy Sauce", 2, "tbsp", "Pantry"),
            ("Garlic", 4, "cloves", "Produce"),
            ("Lemon", 1, "whole", "Produce"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
            ("Green Onion", 2, "stalks", "Produce"),
            ("Sesame Seeds", 1, "tbsp", "Pantry"),
            ("Salt", 0.5, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.25, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 21: Breakfast Burrito
    {
        "recipe_name": "Breakfast Burrito",
        "recipe_category": "American",
        "meal_type": "Breakfast",
        "diet_pref": None,
        "cook_time": 25,
        "servings": 4,
        "directions": """Cook bacon in a large skillet until crispy. Remove and crumble. Keep 1 tbsp drippings.
Add diced potatoes to the skillet and cook until golden and crispy, about 10-12 minutes.
Season potatoes with salt, pepper, and paprika. Remove and set aside.
In the same pan, sauté diced onion and bell pepper until softened.
Whisk eggs with milk, salt, and pepper.
Pour eggs into the pan and scramble until just set.
Warm large flour tortillas on a dry skillet for 30 seconds each side.
Layer each tortilla with scrambled eggs, crispy potatoes, bacon, cheese, and salsa.
Add sliced avocado if desired.
Fold in the sides, then roll up tightly from the bottom.
Cut in half on the diagonal and serve with extra salsa and sour cream.""",
        "notes": "Make ahead and freeze for busy mornings - wrap in foil and reheat in the oven at 350°F for 20 minutes. Add chorizo instead of bacon for a Mexican twist.",
        "ingredients": [
            ("Eggs", 8, "whole", "Dairy & Eggs"),
            ("Bacon", 8, "slices", "Meat & Poultry"),
            ("Flour Tortillas", 4, "large", "Bakery"),
            ("Potatoes", 2, "whole", "Produce"),
            ("Cheddar Cheese", 1, "cup", "Dairy & Eggs"),
            ("Onion", 0.5, "whole", "Produce"),
            ("Bell Pepper", 1, "whole", "Produce"),
            ("Milk", 2, "tbsp", "Dairy & Eggs"),
            ("Salsa", 0.5, "cup", "Condiments"),
            ("Avocado", 1, "whole", "Produce"),
            ("Paprika", 0.5, "tsp", "Spices & Seasonings"),
            ("Salt", 0.5, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.25, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 22: French Onion Soup
    {
        "recipe_name": "French Onion Soup",
        "recipe_category": "French",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 90,
        "servings": 6,
        "directions": """Slice onions into thin half-moons.
Melt butter in a large Dutch oven over medium heat.
Add all the onions and stir to coat with butter.
Cook onions slowly, stirring occasionally, for 45 minutes to 1 hour until deeply caramelized.
Add minced garlic and thyme, cook for 1 minute.
Pour in white wine and scrape up any browned bits from the bottom.
Add beef broth and bay leaves.
Season with salt and pepper.
Simmer for 20 minutes to meld flavors.
Meanwhile, slice baguette and toast lightly.
Preheat broiler.
Ladle soup into oven-safe crocks.
Float 1-2 slices of bread on top of each bowl.
Cover generously with shredded Gruyère cheese.
Broil 3-4 minutes until cheese is bubbly and golden brown.
Serve immediately - bowls will be very hot!""",
        "notes": "Don't rush the onion caramelization - this is what gives the soup its rich, sweet flavor. Use a mix of yellow and sweet onions for best results.",
        "ingredients": [
            ("Yellow Onion", 4, "large", "Produce"),
            ("Butter", 4, "tbsp", "Dairy & Eggs"),
            ("Beef Broth", 8, "cups", "Pantry"),
            ("White Wine", 0.75, "cup", "Beverages"),
            ("Gruyère Cheese", 2, "cups", "Dairy & Eggs"),
            ("Baguette", 1, "whole", "Bakery"),
            ("Garlic", 3, "cloves", "Produce"),
            ("Thyme", 4, "sprigs", "Produce"),
            ("Bay Leaves", 2, "whole", "Spices & Seasonings"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 23: Chicken Parmesan
    {
        "recipe_name": "Chicken Parmesan",
        "recipe_category": "Italian",
        "meal_type": "Dinner",
        "diet_pref": None,
        "cook_time": 45,
        "servings": 4,
        "directions": """Pound chicken breasts to even 1/2-inch thickness between plastic wrap.
Set up breading station: flour in one dish, beaten eggs in another, breadcrumb mixture in third.
Mix breadcrumbs with grated Parmesan, Italian seasoning, garlic powder, salt, and pepper.
Dredge each chicken breast in flour, then egg, then breadcrumb mixture.
Heat olive oil in a large oven-safe skillet over medium-high heat.
Cook breaded chicken for 3-4 minutes per side until golden brown.
Preheat oven to 400°F.
Spoon marinara sauce over each chicken breast.
Top with shredded mozzarella and additional Parmesan.
Bake for 15-20 minutes until cheese is melted and bubbly.
Let rest 5 minutes before serving.
Serve over spaghetti or with crusty bread.
Garnish with fresh basil.""",
        "notes": "For extra crispy coating, use panko breadcrumbs. Let the chicken rest after coating for 5 minutes before frying.",
        "ingredients": [
            ("Chicken Breast", 4, "whole", "Meat & Poultry"),
            ("Mozzarella Cheese", 8, "oz", "Dairy & Eggs"),
            ("Parmesan Cheese", 0.75, "cup", "Dairy & Eggs"),
            ("Marinara Sauce", 2, "cups", "Condiments"),
            ("Panko Bread Crumbs", 1.5, "cups", "Pantry"),
            ("All-Purpose Flour", 0.5, "cup", "Pantry"),
            ("Eggs", 2, "whole", "Dairy & Eggs"),
            ("Italian Seasoning", 1, "tbsp", "Spices & Seasonings"),
            ("Garlic Powder", 1, "tsp", "Spices & Seasonings"),
            ("Olive Oil", 0.5, "cup", "Pantry"),
            ("Basil", 0.25, "cup", "Produce"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 24: Vegetable Lasagna
    {
        "recipe_name": "Vegetable Lasagna",
        "recipe_category": "Italian",
        "meal_type": "Dinner",
        "diet_pref": "Vegetarian",
        "cook_time": 90,
        "servings": 8,
        "directions": """Preheat oven to 375°F.
Slice zucchini and eggplant into 1/4-inch rounds. Salt and let drain for 15 minutes.
Sauté mushrooms and spinach separately in olive oil. Season and set aside.
Mix ricotta with egg, half the Parmesan, and Italian seasoning.
Pat vegetables dry and brush with olive oil.
Grill or roast vegetables until tender, about 3-4 minutes per side.
Spread a thin layer of marinara on bottom of 9x13 baking dish.
Layer: noodles, ricotta mixture, grilled vegetables, mozzarella, marinara.
Repeat layers twice more, ending with noodles, sauce, and cheeses on top.
Cover with foil and bake for 45 minutes.
Remove foil and bake 15 more minutes until bubbly and golden.
Let rest 15 minutes before slicing.
Garnish with fresh basil before serving.""",
        "notes": "No-boil lasagna noodles work great and save time. You can assemble a day ahead and refrigerate - add 15 minutes to bake time if cold.",
        "ingredients": [
            ("Lasagna Noodles", 12, "sheets", "Pantry"),
            ("Ricotta Cheese", 32, "oz", "Dairy & Eggs"),
            ("Mozzarella Cheese", 16, "oz", "Dairy & Eggs"),
            ("Parmesan Cheese", 1, "cup", "Dairy & Eggs"),
            ("Marinara Sauce", 4, "cups", "Condiments"),
            ("Zucchini", 2, "whole", "Produce"),
            ("Eggplant", 1, "whole", "Produce"),
            ("Mushrooms", 8, "oz", "Produce"),
            ("Spinach", 6, "oz", "Produce"),
            ("Eggs", 1, "whole", "Dairy & Eggs"),
            ("Italian Seasoning", 1, "tbsp", "Spices & Seasonings"),
            ("Olive Oil", 3, "tbsp", "Pantry"),
            ("Basil", 0.25, "cup", "Produce"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 25: Chocolate Lava Cake
    {
        "recipe_name": "Chocolate Lava Cake",
        "recipe_category": "Comfort Food",
        "meal_type": "Dessert",
        "diet_pref": "Vegetarian",
        "cook_time": 30,
        "servings": 4,
        "directions": """Preheat oven to 425°F.
Generously butter four 6-ounce ramekins and dust with cocoa powder.
Melt dark chocolate and butter together in a double boiler or microwave, stirring until smooth.
In a bowl, whisk eggs and egg yolks with sugar until thick and pale, about 2 minutes.
Fold the melted chocolate mixture into the egg mixture.
Sift in flour and fold gently until just combined - don't overmix.
Add vanilla extract and a pinch of salt.
Divide batter evenly among prepared ramekins.
Place ramekins on a baking sheet.
Bake for exactly 12-14 minutes - edges should be set but center still soft.
Let cool for 1 minute only.
Run a knife around the edges and invert onto plates.
Dust with powdered sugar and serve immediately with vanilla ice cream or whipped cream.""",
        "notes": "Timing is crucial - even 1 minute too long and you'll lose the molten center. You can prepare the batter ahead and refrigerate - add 2 minutes to bake time if cold.",
        "ingredients": [
            ("Dark Chocolate", 4, "oz", "Pantry"),
            ("Butter", 0.5, "cup", "Dairy & Eggs"),
            ("Eggs", 2, "whole", "Dairy & Eggs"),
            ("Egg Yolks", 2, "whole", "Dairy & Eggs"),
            ("White Sugar", 0.25, "cup", "Pantry"),
            ("All-Purpose Flour", 2, "tbsp", "Pantry"),
            ("Vanilla Extract", 1, "tsp", "Pantry"),
            ("Cocoa Powder", 2, "tbsp", "Pantry"),
            ("Salt", 1, "pinch", "Spices & Seasonings"),
            ("Powdered Sugar", 2, "tbsp", "Pantry"),
        ],
    },

    # Recipe 26: Asian Sesame Chicken Salad
    {
        "recipe_name": "Asian Sesame Chicken Salad",
        "recipe_category": "Asian",
        "meal_type": "Lunch",
        "diet_pref": None,
        "cook_time": 25,
        "servings": 4,
        "directions": """Season chicken breasts with salt, pepper, and five-spice powder.
Grill or pan-sear chicken until cooked through, about 6-7 minutes per side.
Let rest, then slice into strips.
For the dressing: whisk sesame oil, rice vinegar, soy sauce, honey, ginger, and garlic.
In a large bowl, combine mixed greens, shredded cabbage, edamame, and mandarin oranges.
Add julienned carrots and sliced bell pepper.
Toss salad with dressing to coat.
Top with sliced chicken, crispy wonton strips, and toasted almonds.
Sprinkle with sesame seeds and sliced green onions.
Serve immediately.""",
        "notes": "Make crispy wonton strips by cutting wonton wrappers into strips and frying until golden. For meal prep, keep dressing and crunchy toppings separate until serving.",
        "ingredients": [
            ("Chicken Breast", 1, "lb", "Meat & Poultry"),
            ("Mixed Greens", 8, "cups", "Produce"),
            ("Cabbage", 2, "cups", "Produce"),
            ("Carrots", 2, "whole", "Produce"),
            ("Bell Pepper", 1, "whole", "Produce"),
            ("Edamame", 1, "cup", "Frozen"),
            ("Mandarin Oranges", 1, "can", "Pantry"),
            ("Sesame Oil", 2, "tbsp", "Pantry"),
            ("Rice Vinegar", 3, "tbsp", "Pantry"),
            ("Soy Sauce", 2, "tbsp", "Pantry"),
            ("Honey", 1, "tbsp", "Pantry"),
            ("Ginger", 1, "tsp", "Produce"),
            ("Almonds", 0.25, "cup", "Pantry"),
            ("Sesame Seeds", 2, "tbsp", "Pantry"),
        ],
    },

    # Recipe 27: Butternut Squash Soup
    {
        "recipe_name": "Butternut Squash Soup",
        "recipe_category": "Healthy",
        "meal_type": "Lunch",
        "diet_pref": "Vegan",
        "cook_time": 50,
        "servings": 6,
        "directions": """Preheat oven to 400°F.
Cut butternut squash in half, remove seeds, and brush with olive oil.
Place cut-side down on a baking sheet and roast for 40-45 minutes until tender.
Meanwhile, sauté diced onion and apple in butter until softened, about 8 minutes.
Add minced garlic and cook for 1 minute.
Scoop roasted squash flesh into the pot.
Add vegetable broth, maple syrup, and spices.
Bring to a simmer and cook for 10 minutes.
Blend until smooth using an immersion blender or regular blender in batches.
Stir in coconut cream for richness.
Season with salt and pepper to taste.
Serve topped with pepitas, a drizzle of coconut cream, and fresh sage leaves.""",
        "notes": "Pre-cut butternut squash from the store saves significant prep time. For extra depth, add a teaspoon of curry powder.",
        "ingredients": [
            ("Butternut Squash", 2, "lbs", "Produce"),
            ("Vegetable Broth", 4, "cups", "Pantry"),
            ("Coconut Milk", 0.5, "cup", "Pantry"),
            ("Apple", 1, "whole", "Produce"),
            ("Onion", 1, "whole", "Produce"),
            ("Garlic", 3, "cloves", "Produce"),
            ("Maple Syrup", 2, "tbsp", "Pantry"),
            ("Butter", 2, "tbsp", "Dairy & Eggs"),
            ("Sage", 4, "leaves", "Produce"),
            ("Cinnamon", 0.5, "tsp", "Spices & Seasonings"),
            ("Nutmeg", 0.25, "tsp", "Spices & Seasonings"),
            ("Olive Oil", 2, "tbsp", "Pantry"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 28: Grilled Steak with Chimichurri
    {
        "recipe_name": "Grilled Steak with Chimichurri",
        "recipe_category": "American",
        "meal_type": "Dinner",
        "diet_pref": "Gluten-Free",
        "cook_time": 30,
        "servings": 4,
        "directions": """Make chimichurri: finely chop parsley, cilantro, and oregano.
Mix herbs with minced garlic, red pepper flakes, red wine vinegar, and olive oil.
Season generously with salt and pepper. Let sit while you prepare the steak.
Remove steaks from refrigerator 30 minutes before cooking.
Season both sides generously with salt and pepper.
Preheat grill or cast-iron skillet to high heat.
Grill steaks for 4-5 minutes per side for medium-rare (adjust for desired doneness).
Let steaks rest for 5-10 minutes on a cutting board.
Slice against the grain if using flank or skirt steak.
Spoon chimichurri generously over the steak.
Serve with extra chimichurri on the side.
Pair with roasted potatoes or a simple green salad.""",
        "notes": "Chimichurri can be made a day ahead - the flavors intensify overnight. Always slice against the grain for the most tender results.",
        "ingredients": [
            ("Beef Steak", 2, "lbs", "Meat & Poultry"),
            ("Parsley", 1, "cup", "Produce"),
            ("Cilantro", 0.5, "cup", "Produce"),
            ("Oregano", 2, "tbsp", "Produce"),
            ("Garlic", 4, "cloves", "Produce"),
            ("Red Wine Vinegar", 3, "tbsp", "Pantry"),
            ("Olive Oil", 0.5, "cup", "Pantry"),
            ("Red Pepper Flakes", 0.5, "tsp", "Spices & Seasonings"),
            ("Salt", 1, "tbsp", "Spices & Seasonings"),
            ("Black Pepper", 1, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 29: Blueberry Pancakes
    {
        "recipe_name": "Fluffy Blueberry Pancakes",
        "recipe_category": "American",
        "meal_type": "Breakfast",
        "diet_pref": "Vegetarian",
        "cook_time": 25,
        "servings": 4,
        "directions": """In a large bowl, whisk together flour, sugar, baking powder, baking soda, and salt.
In another bowl, whisk buttermilk, milk, egg, melted butter, and vanilla.
Pour wet ingredients into dry ingredients and stir until just combined (lumps are OK).
Fold in blueberries gently.
Heat a griddle or large pan over medium heat and brush with butter.
Pour 1/4 cup batter for each pancake.
Cook until bubbles form on the surface and edges look set, about 2-3 minutes.
Flip and cook another 1-2 minutes until golden brown.
Keep warm in a 200°F oven while cooking remaining pancakes.
Stack pancakes and top with additional blueberries, butter, and maple syrup.
Dust with powdered sugar if desired.""",
        "notes": "Don't overmix the batter - lumps create fluffy pancakes. Fresh or frozen blueberries both work well; no need to thaw frozen ones.",
        "ingredients": [
            ("All-Purpose Flour", 2, "cups", "Pantry"),
            ("Blueberries", 1, "cup", "Produce"),
            ("Buttermilk", 1.5, "cups", "Dairy & Eggs"),
            ("Milk", 0.5, "cup", "Dairy & Eggs"),
            ("Eggs", 1, "whole", "Dairy & Eggs"),
            ("Butter", 4, "tbsp", "Dairy & Eggs"),
            ("White Sugar", 2, "tbsp", "Pantry"),
            ("Baking Powder", 2, "tsp", "Pantry"),
            ("Baking Soda", 0.5, "tsp", "Pantry"),
            ("Vanilla Extract", 1, "tsp", "Pantry"),
            ("Maple Syrup", 0.5, "cup", "Pantry"),
            ("Salt", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },

    # Recipe 30: Spinach and Feta Stuffed Chicken
    {
        "recipe_name": "Spinach and Feta Stuffed Chicken",
        "recipe_category": "Mediterranean",
        "meal_type": "Dinner",
        "diet_pref": "Gluten-Free",
        "cook_time": 40,
        "servings": 4,
        "directions": """Preheat oven to 400°F.
Sauté spinach in a little olive oil until wilted. Let cool and squeeze out excess moisture.
Mix spinach with crumbled feta, cream cheese, minced garlic, and sun-dried tomatoes.
Season filling with salt, pepper, and Italian seasoning.
Cut a horizontal pocket into each chicken breast, being careful not to cut through.
Stuff each breast with the spinach-feta mixture.
Secure with toothpicks if needed.
Season outside of chicken with salt, pepper, and paprika.
Heat olive oil in an oven-safe skillet over medium-high heat.
Sear chicken for 3 minutes per side until golden.
Transfer to oven and bake for 18-22 minutes until internal temperature reaches 165°F.
Let rest 5 minutes before serving.
Garnish with fresh herbs and serve with roasted vegetables.""",
        "notes": "Pounding the chicken slightly before stuffing helps it cook more evenly. The filling can be made a day ahead and refrigerated.",
        "ingredients": [
            ("Chicken Breast", 4, "whole", "Meat & Poultry"),
            ("Spinach", 6, "oz", "Produce"),
            ("Feta Cheese", 4, "oz", "Dairy & Eggs"),
            ("Cream Cheese", 2, "oz", "Dairy & Eggs"),
            ("Sun-Dried Tomatoes", 0.25, "cup", "Pantry"),
            ("Garlic", 3, "cloves", "Produce"),
            ("Olive Oil", 3, "tbsp", "Pantry"),
            ("Italian Seasoning", 1, "tsp", "Spices & Seasonings"),
            ("Paprika", 1, "tsp", "Spices & Seasonings"),
            ("Salt", 1, "tsp", "Spices & Seasonings"),
            ("Black Pepper", 0.5, "tsp", "Spices & Seasonings"),
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# MEAL SELECTION DATA
# ══════════════════════════════════════════════════════════════════════════════════════════════════

MEAL_SELECTIONS_DATA = [
    {"name": "Sunday Family Dinner", "main": "Classic Spaghetti Bolognese", "sides": ["Classic Caesar Salad", "Caprese Salad"]},
    {"name": "Quick Weeknight", "main": "Honey Garlic Salmon", "sides": []},
    {"name": "Date Night Special", "main": "Grilled Steak with Chimichurri", "sides": ["Mushroom Risotto"]},
    {"name": "Taco Tuesday", "main": "Beef Tacos with Fresh Salsa", "sides": []},
    {"name": "Asian Fusion Night", "main": "Thai Green Curry", "sides": ["Vegetable Stir Fry with Tofu"]},
    {"name": "Italian Feast", "main": "Chicken Parmesan", "sides": ["Classic Caesar Salad", "Caprese Salad"]},
    {"name": "Healthy Monday", "main": "Greek Salad with Grilled Chicken", "sides": ["Butternut Squash Soup"]},
    {"name": "Comfort Food Sunday", "main": "Shepherd's Pie", "sides": ["Creamy Tomato Soup"]},
    {"name": "Seafood Saturday", "main": "Fish Tacos with Mango Salsa", "sides": []},
    {"name": "Weekend Brunch", "main": "Breakfast Burrito", "sides": ["Fluffy Blueberry Pancakes"]},
]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# SHOPPING DATA
# ══════════════════════════════════════════════════════════════════════════════════════════════════

SHOPPING_ITEMS_DATA = [
    # Recipe-sourced items
    {"name": "Chicken Breast", "qty": 2, "unit": "lbs", "category": "Meat & Poultry", "source": "recipe", "have": False},
    {"name": "Ground Beef", "qty": 1, "unit": "lb", "category": "Meat & Poultry", "source": "recipe", "have": False},
    {"name": "Salmon Fillet", "qty": 4, "unit": "fillets", "category": "Seafood", "source": "recipe", "have": True},
    {"name": "Onions", "qty": 5, "unit": "whole", "category": "Produce", "source": "recipe", "have": False},
    {"name": "Garlic", "qty": 2, "unit": "heads", "category": "Produce", "source": "recipe", "have": True},
    {"name": "Tomatoes", "qty": 6, "unit": "whole", "category": "Produce", "source": "recipe", "have": False},
    {"name": "Olive Oil", "qty": 1, "unit": "bottle", "category": "Pantry", "source": "recipe", "have": True},
    {"name": "Parmesan Cheese", "qty": 8, "unit": "oz", "category": "Dairy & Eggs", "source": "recipe", "have": False},
    {"name": "Heavy Cream", "qty": 1, "unit": "pint", "category": "Dairy & Eggs", "source": "recipe", "have": False},
    {"name": "Fresh Basil", "qty": 1, "unit": "bunch", "category": "Produce", "source": "recipe", "have": False},
    # Manual items
    {"name": "Paper Towels", "qty": 2, "unit": "rolls", "category": None, "source": "manual", "have": False},
    {"name": "Dish Soap", "qty": 1, "unit": "bottle", "category": None, "source": "manual", "have": False},
    {"name": "Coffee", "qty": 1, "unit": "bag", "category": "Beverages", "source": "manual", "have": True},
    {"name": "Bread", "qty": 1, "unit": "loaf", "category": "Bakery", "source": "manual", "have": False},
    {"name": "Eggs", "qty": 1, "unit": "dozen", "category": "Dairy & Eggs", "source": "manual", "have": False},
    {"name": "Butter", "qty": 1, "unit": "stick", "category": "Dairy & Eggs", "source": "manual", "have": True},
    {"name": "Milk", "qty": 1, "unit": "gallon", "category": "Dairy & Eggs", "source": "manual", "have": False},
    {"name": "Bananas", "qty": 1, "unit": "bunch", "category": "Produce", "source": "manual", "have": False},
]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# SEEDING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def clear_all_data(session: Session, models: Dict[str, Any], verbose: bool = False) -> None:
    """Clear all data from tables in correct order (respecting foreign keys)."""
    tables_to_clear = [
        ("shopping_item_contributions", models["ShoppingItemContribution"]),
        ("shopping_items", models["ShoppingItem"]),
        ("planner_entries", models["PlannerEntry"]),
        ("meals", models["Meal"]),
        ("recipe_ingredients", models["RecipeIngredient"]),
        ("recipes", models["Recipe"]),
        ("ingredients", models["Ingredient"]),
    ]

    for table_name, model in tables_to_clear:
        try:
            count = session.query(model).delete()
            if verbose:
                print(f"  [OK] Cleared {table_name} ({count} rows)")
        except Exception as e:
            # Table might not exist yet (migrations not run)
            session.rollback()
            if verbose:
                print(f"  [SKIP] {table_name} (table may not exist)")
    session.commit()


def seed_ingredients(
    session: Session,
    models: Dict[str, Any],
    verbose: bool = False
) -> Dict[Tuple[str, str], Any]:
    """Seed all ingredients from the data and return a lookup dict."""
    Ingredient = models["Ingredient"]
    ingredient_map: Dict[Tuple[str, str], Any] = {}

    for category, names in INGREDIENTS_BY_CATEGORY.items():
        for name in names:
            key = (name.lower(), category)
            if key not in ingredient_map:
                ingredient = Ingredient(
                    ingredient_name=name,
                    ingredient_category=category
                )
                session.add(ingredient)
                ingredient_map[key] = ingredient

    session.commit()

    # Refresh to get IDs
    for ingredient in ingredient_map.values():
        session.refresh(ingredient)

    if verbose:
        print(f"  [OK] Created {len(ingredient_map)} ingredients")

    return ingredient_map


def get_or_create_ingredient(
    session: Session,
    models: Dict[str, Any],
    ingredient_map: Dict[Tuple[str, str], Any],
    name: str,
    category: str
) -> Any:
    """Get an existing ingredient or create a new one."""
    Ingredient = models["Ingredient"]
    key = (name.lower(), category)
    if key in ingredient_map:
        return ingredient_map[key]

    # Create new ingredient
    ingredient = Ingredient(
        ingredient_name=name,
        ingredient_category=category
    )
    session.add(ingredient)
    session.flush()
    ingredient_map[key] = ingredient
    return ingredient


def seed_recipes(
    session: Session,
    models: Dict[str, Any],
    ingredient_map: Dict[Tuple[str, str], Any],
    count: int = 25,
    verbose: bool = False
) -> List[Any]:
    """Seed recipes with their ingredients."""
    Recipe = models["Recipe"]
    RecipeIngredient = models["RecipeIngredient"]

    recipes_to_seed = RECIPES_DATA[:count] if count < len(RECIPES_DATA) else RECIPES_DATA
    created_recipes: List[Any] = []

    for idx, recipe_data in enumerate(recipes_to_seed, start=1):
        # Randomly set some as favorites (about 20%)
        is_favorite = random.random() < 0.2

        recipe = Recipe(
            recipe_name=recipe_data["recipe_name"],
            recipe_category=recipe_data["recipe_category"],
            meal_type=recipe_data["meal_type"],
            diet_pref=recipe_data.get("diet_pref"),
            cook_time=recipe_data.get("cook_time"),
            servings=recipe_data["servings"],
            directions=recipe_data["directions"],
            notes=recipe_data.get("notes"),
            reference_image_path=f"/images/recipes/{idx}.png",
            banner_image_path=f"/images/recipes/{idx}_banner.png",
            is_favorite=is_favorite,
        )
        session.add(recipe)
        session.flush()  # Get the ID

        # Add ingredients
        for ing_name, quantity, unit, category in recipe_data["ingredients"]:
            ingredient = get_or_create_ingredient(session, models, ingredient_map, ing_name, category)
            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=quantity,
                unit=unit
            )
            session.add(recipe_ingredient)

        created_recipes.append(recipe)

        if verbose:
            ing_count = len(recipe_data["ingredients"])
            fav_marker = " [FAV]" if is_favorite else ""
            print(f"  [OK] Created: {recipe.recipe_name} ({ing_count} ingredients){fav_marker}")

    session.commit()

    if verbose:
        print(f"  [OK] Created {len(created_recipes)} recipes total")

    return created_recipes


def seed_meal_selections(
    session: Session,
    models: Dict[str, Any],
    recipes: List[Any],
    verbose: bool = False
) -> Tuple[List[Any], List[Any]]:
    """Seed meals and planner entries."""
    Meal = models["Meal"]
    PlannerEntry = models["PlannerEntry"]

    recipe_by_name = {r.recipe_name: r for r in recipes}
    created_meals: List[Any] = []
    created_entries: List[Any] = []

    for meal_data in MEAL_SELECTIONS_DATA:
        main_recipe = recipe_by_name.get(meal_data["main"])
        if not main_recipe:
            continue

        sides = meal_data.get("sides", [])
        side_ids = [recipe_by_name.get(s) for s in sides if recipe_by_name.get(s)]

        meal = Meal(
            meal_name=meal_data["name"],
            main_recipe_id=main_recipe.id,
        )
        # Set side recipe IDs using the property (stores as JSON)
        meal.side_recipe_ids = [s.id for s in side_ids]
        session.add(meal)
        created_meals.append(meal)

    session.flush()

    # Add some meals to planner (about half)
    meals_to_plan = random.sample(created_meals, min(len(created_meals) // 2 + 1, len(created_meals)))
    for meal in meals_to_plan:
        planner_entry = PlannerEntry(meal_id=meal.id)
        session.add(planner_entry)
        created_entries.append(planner_entry)

    session.commit()

    if verbose:
        print(f"  [OK] Created {len(created_meals)} meals")
        print(f"  [OK] Added {len(created_entries)} meals to planner")

    return created_meals, created_entries


def seed_shopping_data(
    session: Session,
    models: Dict[str, Any],
    verbose: bool = False
) -> Tuple[List[Any], List[Any]]:
    """Seed shopping items (manual items only - recipe items come from sync)."""
    ShoppingItem = models["ShoppingItem"]

    created_items: List[Any] = []

    for item_data in SHOPPING_ITEMS_DATA:
        # Only seed manual items - recipe items will be created by sync
        if item_data["source"] == "manual":
            item = ShoppingItem(
                ingredient_name=item_data["name"],
                quantity=item_data["qty"],
                unit=item_data["unit"],
                category=item_data.get("category"),
                source=item_data["source"],
                have=item_data["have"],
            )
            session.add(item)
            created_items.append(item)

    session.commit()

    if verbose:
        print(f"  [OK] Created {len(created_items)} manual shopping items")

    return created_items, []


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN CLI
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Enchanted Spoon Database Seeder - Populate the database with realistic mock data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_database.py --mode replace           # Clear and reseed all data
  python seed_database.py --mode append --count 10 # Add 10 more recipes
  python seed_database.py --recipes-only --verbose # Only seed recipes with detailed output
  python seed_database.py --clear-only             # Clear all data without reseeding
        """
    )

    parser.add_argument(
        "--mode",
        choices=["replace", "append"],
        default="replace",
        help="'replace' clears all data first (default), 'append' adds to existing data"
    )

    parser.add_argument(
        "--recipes-only",
        action="store_true",
        help="Only seed recipes and ingredients (skip meal plans, shopping)"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of recipes to seed (default: 25, min: 25 for replace mode)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output during seeding"
    )

    parser.add_argument(
        "--clear-only",
        action="store_true",
        help="Only clear all data from the database (no seeding)"
    )

    args = parser.parse_args()

    # Validate count (skip if clear-only)
    if not args.clear_only and args.mode == "replace" and args.count < 25:
        print("Warning: Minimum recipe count for replace mode is 25. Using 25.")
        args.count = 25

    # Header
    print()
    if args.clear_only:
        print("Enchanted Spoon Database Clearer")
        print("=" * 25)
        print("Mode: clear-only")
    else:
        print("Enchanted Spoon Database Seeder")
        print("=" * 24)
        print(f"Mode: {args.mode}")
        print(f"Recipe count: {args.count}")
        if args.recipes_only:
            print("Recipes only: Yes")
    print()

    # Lazy load database and models to avoid circular imports
    SessionLocal, models = get_db_and_models()
    session = SessionLocal()

    try:
        # Handle clear-only mode
        if args.clear_only:
            print("Clearing all data...")
            clear_all_data(session, models, verbose=args.verbose)
            print()
            print("Database cleared successfully!")
            print()
            return

        # Clear data if replace mode
        if args.mode == "replace":
            print("Clearing existing data...")
            clear_all_data(session, models, verbose=args.verbose)
            print()

        # Seed ingredients
        print("Seeding ingredients...")
        ingredient_map = seed_ingredients(session, models, verbose=args.verbose)
        total_ingredients = len(ingredient_map)
        print()

        # Seed recipes
        print("Seeding recipes...")
        recipes = seed_recipes(session, models, ingredient_map, count=args.count, verbose=args.verbose)
        total_recipes = len(recipes)
        print()

        # Seed meal selections and shopping unless recipes-only
        total_meals = 0
        total_saved = 0
        total_shopping = 0

        if not args.recipes_only:
            print("Seeding meal selections...")
            meals, saved_states = seed_meal_selections(session, models, recipes, verbose=args.verbose)
            total_meals = len(meals)
            total_saved = len(saved_states)
            print()

            print("Seeding shopping data...")
            shopping_items, _ = seed_shopping_data(session, models, verbose=args.verbose)
            total_shopping = len(shopping_items)
            print()

        # Summary
        print("Database seeding complete!")
        print("Summary:")
        print(f"  - Recipes: {total_recipes}")
        print(f"  - Ingredients: {total_ingredients}")
        if not args.recipes_only:
            print(f"  - Meals: {total_meals}")
            print(f"  - Planner Entries: {total_saved}")
            print(f"  - Shopping Items: {total_shopping}")
        print()

    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
