// Illustrative dishes for the public landing page. These are examples of what
// a person can save and plan — not a customer's account, reviews, or counts.

export interface ExampleRecipe {
  name: string;
  image: string;
  servings: number;
  time: string;
  mealType: string;
}

export interface ExampleIngredient {
  name: string;
  qty: string;
  source: string;
}

export const SHRIMP_PASTA: ExampleRecipe = {
  name: "Garlic Butter Shrimp Pasta",
  image: "/images/landing/food/shrimp-pasta.jpg",
  servings: 4,
  time: "30 min",
  mealType: "Dinner",
};

export const AVOCADO_CORN_SALAD: ExampleRecipe = {
  name: "Avocado Corn Salad",
  image: "/images/landing/food/avocado-corn-salad.jpg",
  servings: 4,
  time: "10 min",
  mealType: "Side",
};

export const RIBEYE_STEAK: ExampleRecipe = {
  name: "Ribeye Steak",
  image: "/images/landing/food/ribeye-steak.jpg",
  servings: 2,
  time: "30 min",
  mealType: "Dinner",
};

export const AIR_FRYER_POTATOES: ExampleRecipe = {
  name: "Air Fryer Potatoes",
  image: "/images/landing/food/air-fryer-potatoes.jpg",
  servings: 3,
  time: "25 min",
  mealType: "Side",
};

export const FISH_SANDWICHES: ExampleRecipe = {
  name: "Fish Sandwiches",
  image: "/images/landing/food/fish-sandwiches.jpg",
  servings: 4,
  time: "35 min",
  mealType: "Dinner",
};

export const STUFFED_CHICKEN: ExampleRecipe = {
  name: "Spinach Stuffed Chicken Thighs",
  image: "/images/landing/food/stuffed-chicken.jpg",
  servings: 4,
  time: "45 min",
  mealType: "Dinner",
};

export const BBQ_CHICKEN_BOWL: ExampleRecipe = {
  name: "BBQ Chicken Protein Bowl",
  image: "/images/landing/food/bbq-chicken-bowl.jpg",
  servings: 4,
  time: "20 min",
  mealType: "Dinner",
};

export const APPLE_COBBLER: ExampleRecipe = {
  name: "Apple Cobbler",
  image: "/images/landing/food/apple-cobbler.jpg",
  servings: 6,
  time: "1 hr",
  mealType: "Dessert",
};

export const TUESDAY_INGREDIENTS: ExampleIngredient[] = [
  { name: "Shrimp", qty: "1 lb", source: "Garlic Butter Shrimp Pasta" },
  { name: "Spaghetti", qty: "12 oz", source: "Garlic Butter Shrimp Pasta" },
  { name: "Garlic", qty: "4 cloves", source: "Garlic Butter Shrimp Pasta" },
  { name: "Butter", qty: "3 tbsp", source: "Garlic Butter Shrimp Pasta" },
  { name: "Avocado", qty: "2", source: "Avocado Corn Salad" },
  { name: "Corn", qty: "2 cups", source: "Avocado Corn Salad" },
];

export interface ExampleNight {
  day: string;
  recipes: ExampleRecipe[];
  note?: string;
}

export const EXAMPLE_WEEK: ExampleNight[] = [
  { day: "Mon", recipes: [RIBEYE_STEAK, AIR_FRYER_POTATOES] },
  { day: "Tue", recipes: [SHRIMP_PASTA, AVOCADO_CORN_SALAD] },
  { day: "Wed", recipes: [FISH_SANDWICHES] },
  { day: "Thu", recipes: [STUFFED_CHICKEN] },
  { day: "Fri", recipes: [BBQ_CHICKEN_BOWL] },
  { day: "Sat", recipes: [APPLE_COBBLER], note: "Dessert" },
  { day: "Sun", recipes: [], note: "Open night" },
];
