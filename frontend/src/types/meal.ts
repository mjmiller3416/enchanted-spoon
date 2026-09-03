// src/types/meal.ts

import type { RecipeCardDTO } from "./recipe";

// ============================================================================
// Meal Planning Types
// ============================================================================

export interface MealSelectionBaseDTO {
  meal_name: string;
  main_recipe_id: number;
  side_recipe_ids: number[];
  is_saved: boolean;
  tags: string[];
}

export interface MealSelectionResponseDTO extends MealSelectionBaseDTO {
  id: number;
  created_at: string | null;
  main_recipe: RecipeCardDTO | null;
  side_recipes: RecipeCardDTO[];
  // Computed stats (calculated on the fly by backend)
  total_cook_time: number | null;
  avg_servings: number | null;
  times_cooked: number | null;
  last_cooked: string | null;
}

export interface MealSelectionCreateDTO {
  meal_name: string;
  main_recipe_id: number;
  side_recipe_ids?: number[];
  is_saved?: boolean;
  tags?: string[];
}

export interface MealSelectionUpdateDTO {
  meal_name?: string;
  main_recipe_id?: number;
  side_recipe_ids?: number[];
  is_saved?: boolean;
  tags?: string[];
}

export interface MealPlanSummaryDTO {
  total_entries: number;
  completed_entries: number;
  incomplete_entries: number;
  total_recipes: number;
  meal_names: string[];
  is_at_capacity: boolean;
  max_capacity: number;
  error: string | null;
}

export interface MealPlanSaveResultDTO {
  success: boolean;
  saved_count: number;
  invalid_ids: number[];
  message: string;
}
