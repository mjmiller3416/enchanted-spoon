// Sample dishes for the public landing page demos. Everything here is made-up
// demo content, not data from a real account.

export interface ExampleRecipe {
  name: string;
  image: string;
  time: string;
}

export const SHRIMP_PASTA: ExampleRecipe = {
  name: "Garlic Butter Shrimp Pasta",
  image: "/images/landing/food/shrimp-pasta.jpg",
  time: "30 min",
};

export const AVOCADO_CORN_SALAD: ExampleRecipe = {
  name: "Avocado Corn Salad",
  image: "/images/landing/food/avocado-corn-salad.jpg",
  time: "10 min",
};

export const RIBEYE_STEAK: ExampleRecipe = {
  name: "Ribeye Steak",
  image: "/images/landing/food/ribeye-steak.jpg",
  time: "30 min",
};

export const AIR_FRYER_POTATOES: ExampleRecipe = {
  name: "Air Fryer Potatoes",
  image: "/images/landing/food/air-fryer-potatoes.jpg",
  time: "25 min",
};

export const FISH_SANDWICHES: ExampleRecipe = {
  name: "Crispy Fish Sandwiches",
  image: "/images/landing/food/fish-sandwiches.jpg",
  time: "35 min",
};

export const STUFFED_CHICKEN: ExampleRecipe = {
  name: "Spinach Stuffed Chicken",
  image: "/images/landing/food/stuffed-chicken.jpg",
  time: "45 min",
};

export const BBQ_CHICKEN_BOWL: ExampleRecipe = {
  name: "BBQ Chicken Bowls",
  image: "/images/landing/food/bbq-chicken-bowl.jpg",
  time: "20 min",
};

export const APPLE_COBBLER: ExampleRecipe = {
  name: "Apple Cobbler",
  image: "/images/landing/food/apple-cobbler.jpg",
  time: "1 hr",
};

/* ------------------------------------------------------------------ */
/* Hero demo: a week of dinners and the grocery list it produces.      */
/* ------------------------------------------------------------------ */

export interface PlannedNight {
  day: string;
  main: ExampleRecipe;
  side?: ExampleRecipe;
}

export const PLANNED_WEEK: PlannedNight[] = [
  { day: "Mon", main: RIBEYE_STEAK, side: AIR_FRYER_POTATOES },
  { day: "Tue", main: SHRIMP_PASTA, side: AVOCADO_CORN_SALAD },
  { day: "Wed", main: STUFFED_CHICKEN },
  { day: "Thu", main: FISH_SANDWICHES },
];

/** The dinner the hero demo drops onto Friday. */
export const FRIDAY_NIGHT: PlannedNight = { day: "Fri", main: BBQ_CHICKEN_BOWL };

export interface ListItem {
  name: string;
  /** Amount before Friday is planned (omit for items Friday adds). */
  before?: string;
  /** Amount after Friday is planned (omit when Friday doesn't touch it). */
  after?: string;
  /** How many planned recipes use it, before → after. */
  recipes: [number, number];
}

export const GROCERY_LIST: ListItem[] = [
  { name: "BBQ sauce", after: "1 cup", recipes: [0, 1] },
  { name: "Red onion", after: "1", recipes: [0, 1] },
  { name: "Chicken thighs", before: "2 lb", after: "3½ lb", recipes: [1, 2] },
  { name: "Corn", before: "2 cups", after: "3 cups", recipes: [1, 2] },
  { name: "Shrimp", before: "1 lb", recipes: [1, 1] },
  { name: "Baby spinach", before: "5 oz", recipes: [1, 1] },
  { name: "Avocados", before: "2", recipes: [1, 1] },
  { name: "Lemons", before: "3", recipes: [2, 2] },
];

export const LIST_TOTAL_BEFORE = 23;
export const LIST_TOTAL_AFTER = 25;
