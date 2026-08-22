"use client";

import { useCallback } from "react";
import { getRecipeIcon } from "@/lib/recipeIcon";
import type { RecipeIconData } from "@/components/common/RecipeIcon";
import { useLocalStorageState } from "./useLocalStorageState";

// ============================================================================
// TYPES
// ============================================================================

export interface RecentRecipe {
  id: number;
  name: string;
  icon: RecipeIconData;
  viewedAt: number; // timestamp for ordering
}

// ============================================================================
// CONSTANTS
// ============================================================================

const STORAGE_KEY = "enchanted-spoon-recent-recipes";
// Pre-rename key, migrated on first load — drop after 1-2 releases
const LEGACY_STORAGE_KEY = "meal-genie-recent-recipes";
const MAX_RECENT_RECIPES = 3;

// ============================================================================
// MIGRATION HELPERS
// ============================================================================

/** Old format stored emoji as string */
interface LegacyRecentRecipe {
  id: number;
  name: string;
  emoji?: string;
  icon?: RecipeIconData;
  viewedAt: number;
}

/**
 * Migrate old localStorage format (emoji: string) to new format (icon: RecipeIconData)
 */
function migrateRecipe(recipe: LegacyRecentRecipe): RecentRecipe {
  // Already in new format
  if (recipe.icon && typeof recipe.icon === "object" && "type" in recipe.icon) {
    return recipe as RecentRecipe;
  }

  // Migrate from old emoji format
  return {
    id: recipe.id,
    name: recipe.name,
    icon: getRecipeIcon(recipe.name),
    viewedAt: recipe.viewedAt,
  };
}

/**
 * Deserialize + migrate raw localStorage data into RecentRecipe[].
 * Defined at module level for a stable reference (avoids effect re-runs).
 */
function deserializeRecipes(raw: unknown): RecentRecipe[] {
  const parsed = raw as LegacyRecentRecipe[];
  return parsed
    .map(migrateRecipe)
    .sort((a, b) => b.viewedAt - a.viewedAt)
    .slice(0, MAX_RECENT_RECIPES);
}

// ============================================================================
// HOOK
// ============================================================================

interface UseRecentRecipesReturn {
  /**
   * List of recently viewed recipes (most recent first)
   */
  recentRecipes: RecentRecipe[];
  /**
   * Whether the hook has loaded from storage
   */
  isLoaded: boolean;
  /**
   * Add a recipe to the recent list
   */
  addToRecent: (recipe: { id: number; name: string; category?: string }) => void;
  /**
   * Remove a recipe from the recent list
   */
  removeFromRecent: (id: number) => void;
  /**
   * Clear all recent recipes
   */
  clearRecent: () => void;
}

/**
 * Hook for tracking recently viewed recipes in localStorage.
 *
 * @example
 * ```tsx
 * const { recentRecipes, addToRecent } = useRecentRecipes();
 *
 * // When viewing a recipe detail page
 * useEffect(() => {
 *   addToRecent({ id: recipe.id, name: recipe.name, category: recipe.category });
 * }, [recipe.id]);
 * ```
 */
export function useRecentRecipes(): UseRecentRecipesReturn {
  // Note: maxItems is intentionally omitted here. Newest recipes are prepended,
  // so truncation uses .slice(0, N) inside addToRecent (keep first N) rather
  // than useLocalStorageState's .slice(-N) (keep last N).
  const [recentRecipes, setRecentRecipes, isLoaded] = useLocalStorageState<RecentRecipe[]>(
    STORAGE_KEY,
    [],
    { deserialize: deserializeRecipes, legacyKey: LEGACY_STORAGE_KEY }
  );

  const addToRecent = useCallback(
    (recipe: { id: number; name: string; category?: string }) => {
      setRecentRecipes((prev) => {
        const filtered = prev.filter((r) => r.id !== recipe.id);
        const newRecipe: RecentRecipe = {
          id: recipe.id,
          name: recipe.name,
          icon: getRecipeIcon(recipe.name, recipe.category),
          viewedAt: Date.now(),
        };
        return [newRecipe, ...filtered].slice(0, MAX_RECENT_RECIPES);
      });
    },
    [setRecentRecipes]
  );

  const removeFromRecent = useCallback(
    (id: number) => {
      setRecentRecipes((prev) => prev.filter((r) => r.id !== id));
    },
    [setRecentRecipes]
  );

  const clearRecent = useCallback(() => {
    setRecentRecipes([]);
  }, [setRecentRecipes]);

  return {
    recentRecipes,
    isLoaded,
    addToRecent,
    removeFromRecent,
    clearRecent,
  };
}
