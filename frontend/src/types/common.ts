// src/types/common.ts

// ============================================================================
// Data Management Types (Import/Export)
// ============================================================================

export type DuplicateAction = "skip" | "update" | "rename";

export interface DuplicateRecipeDTO {
  recipe_name: string;
  recipe_category: string;
  existing_id: number;
  row_number: number;
}

export interface ValidationErrorDTO {
  row_number: number;
  field: string;
  message: string;
}

export interface ImportPreviewDTO {
  total_recipes: number;
  new_recipes: number;
  duplicate_recipes: DuplicateRecipeDTO[];
  validation_errors: ValidationErrorDTO[];
}

export interface ImportResultDTO {
  success: boolean;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  errors: string[];
}

export interface DuplicateResolutionDTO {
  recipe_name: string;
  recipe_category: string;
  action: DuplicateAction;
  new_name?: string;
}

export interface ExportFilterDTO {
  recipe_category?: string | null;
  meal_type?: string | null;
  favorites_only?: boolean;
}

// ============================================================================
// Full Backup Types
// ============================================================================

export interface IngredientBackup {
  id: number;
  ingredient_name: string;
  ingredient_category: string;
}

export interface RecipeBackup {
  id: number;
  recipe_name: string;
  recipe_category: string;
  meal_type: string;
  diet_pref: string | null;
  total_time: number | null;
  servings: number | null;
  directions: string | null;
  notes: string | null;
  reference_image_path: string | null;
  banner_image_path: string | null;
  created_at: string;
  is_favorite: boolean;
}

export interface RecipeIngredientBackup {
  recipe_id: number;
  ingredient_id: number;
  quantity: number | null;
  unit: string | null;
}

export interface RecipeHistoryBackup {
  id: number;
  recipe_id: number;
  cooked_at: string;
}

export interface MealBackup {
  id: number;
  meal_name: string;
  main_recipe_id: number;
  side_recipe_ids: number[];
  tags: string[];
  is_saved: boolean;
  created_at: string;
}

export interface PlannerEntryBackup {
  id: number;
  meal_id: number;
  position: number;
  is_completed: boolean;
  completed_at: string | null;
  scheduled_date: string | null;
  shopping_mode: string;
  is_cleared: boolean;
}

export interface ShoppingItemBackup {
  id: number;
  ingredient_name: string;
  quantity: number;
  unit: string | null;
  category: string | null;
  source: string;
  have: boolean;
  flagged: boolean;
  state_key: string | null;
  recipe_sources: RecipeSourceDTO[] | null;
}

export interface ShoppingStateBackup {
  id: number;
  key: string;
  quantity: number;
  unit: string;
  checked: boolean;
  flagged: boolean;
}

export interface BackupData {
  ingredients: IngredientBackup[];
  recipes: RecipeBackup[];
  recipe_ingredients: RecipeIngredientBackup[];
  recipe_history: RecipeHistoryBackup[];
  meals: MealBackup[];
  planner_entries: PlannerEntryBackup[];
  shopping_items: ShoppingItemBackup[];
  shopping_states: ShoppingStateBackup[];
}

export interface FullBackup {
  version: string;
  created_at: string;
  app_name: string;
  settings: Record<string, unknown> | null;
  data: BackupData;
}

export interface RestorePreview {
  backup_version: string;
  backup_created_at: string;
  counts: Record<string, number>;
  has_settings: boolean;
  warnings: string[];
}

export interface RestoreResult {
  success: boolean;
  restored_counts: Record<string, number>;
  errors: string[];
  settings: Record<string, unknown> | null;
}

// ============================================================================
// Utility Types
// ============================================================================

export interface ValidationResult {
  is_valid: boolean;
  error_message: string;
}

export interface ApiError {
  message: string;
  status: number;
  details?: Record<string, unknown>;
}

export interface BulkOperationResultDTO {
  success: boolean;
  updated_count: number;
  message: string;
  errors?: string[];
}

// ============================================================================
// Feedback Types
// ============================================================================

export interface FeedbackSubmitDTO {
  category: string;
  message: string;
  /** Optional metadata included with feedback (e.g., page URL, viewport) */
  metadata?: Record<string, string | undefined>;
}

export interface FeedbackResponseDTO {
  success: boolean;
  message: string;
  issue_url?: string;
}

// ============================================================================
// Unit Conversion Types
// ============================================================================

export interface UnitOptionDTO {
  value: string;
  label: string;
}

export interface UnitsResponseDTO {
  units: UnitOptionDTO[];
}

export interface UnitConversionRuleDTO {
  id: number;
  ingredient_name: string;
  from_unit: string;
  to_unit: string;
  factor: number;
  round_up: boolean;
  created_at: string;
}

export interface UnitConversionRuleCreateDTO {
  ingredient_name: string;
  from_unit: string;
  to_unit: string;
  factor: number;
  round_up?: boolean;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardStatsDTO {
  total_recipes: number;
  favorites: number;
  meals_planned: number;
  shopping_items: number;
}

// ============================================================================
// Sample Data (onboarding starter pack)
// ============================================================================

export interface SampleDataStatusDTO {
  has_sample_data: boolean;
  recipe_count: number;
  meal_count: number;
}

export interface SampleDataSeedResultDTO {
  recipes_created: number;
  meals_created: number;
  planner_entries_created: number;
}

export interface SampleDataRemovalResultDTO {
  recipes_removed: number;
  meals_removed: number;
  /** Sample recipes kept because one of the user's own meals uses them */
  recipes_kept: number;
}

// ============================================================================
// Re-export RecipeSourceDTO for backward compatibility in backup types
// ============================================================================

import type { RecipeSourceDTO } from "./shopping";
export type { RecipeSourceDTO };
