// src/types/shopping.ts

// ============================================================================
// Shopping List Types
// ============================================================================

/**
 * "recipe" and "manual" are in-app sources; any other string is the slug of a
 * trusted external app that pushed the item (e.g. "tada").
 */
export type ShoppingSource = "recipe" | "manual" | (string & {});

/** Shopping mode for planner entries - controls ingredient inclusion in shopping list */
export type ShoppingMode = "all" | "produce_only" | "none";

export interface ShoppingItemBaseDTO {
  ingredient_name: string;
  quantity: number;
  unit: string | null;
  category: string | null;
}

/** A recipe source with usage count (e.g., same side dish used twice) */
export interface RecipeSourceDTO {
  recipe_name: string;
  count: number;
}

export interface ShoppingItemResponseDTO extends ShoppingItemBaseDTO {
  id: number;
  source: ShoppingSource;
  have: boolean;
  flagged: boolean;
  state_key: string | null;
  recipe_sources: RecipeSourceDTO[];  // Recipe sources with usage counts
}

export interface ShoppingListResponseDTO {
  items: ShoppingItemResponseDTO[];
  total_items: number;
  checked_items: number;
  recipe_items: number;
  manual_items: number;
  categories: string[];
}

export interface ShoppingListGenerationResultDTO {
  success: boolean;
  items_created: number;
  items_updated: number;
  total_items: number;
  message: string;
  errors: string[];
  items: ShoppingItemResponseDTO[];
}

export interface ManualItemCreateDTO {
  ingredient_name: string;
  quantity: number;
  unit?: string | null;
  category?: string | null;
}

export interface ShoppingItemUpdateDTO {
  ingredient_name?: string;
  quantity?: number;
  unit?: string | null;
  category?: string | null;
  have?: boolean;
  flagged?: boolean;
}

export interface ShoppingListFilterDTO {
  source?: ShoppingSource;
  category?: string;
  have?: boolean;
  search_term?: string;
  limit?: number;
  offset?: number;
}

export interface ShoppingListGenerationDTO {
  recipe_ids: number[];
  include_manual_items?: boolean;
  clear_existing?: boolean;
}

/** Free-text notes pad on the shopping list. updated_at is null until first save. */
export interface ShoppingNotesDTO {
  content: string;
  updated_at: string | null;
}
