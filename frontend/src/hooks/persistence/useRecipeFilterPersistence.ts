"use client";

import { useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { accountStorageKey } from "@/lib/account-storage";
import type { RecipeFilters } from "@/lib/filterUtils";
import type {
  SortOption,
  SortDirection,
} from "@/components/recipe/browser/FilterSortControls";

// ============================================================================
// Types
// ============================================================================

export interface SavedRecipeFilterState {
  filters: RecipeFilters;
  searchTerm: string;
  activeQuickFilters: string[];
  sortBy: SortOption;
  sortDirection: SortDirection;
  page?: { key: string; index: number };
  timestamp: number;
}

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = "recipe-browser-filter-state";
const MAX_AGE_MS = 30 * 60 * 1000; // 30 minutes

// ============================================================================
// Hook
// ============================================================================

interface UseRecipeFilterPersistenceReturn {
  /**
   * Save current filter state to sessionStorage
   */
  saveFilterState: (state: Omit<SavedRecipeFilterState, "timestamp">) => void;
  /**
   * Load saved filter state from sessionStorage (returns null if none or stale)
   */
  loadFilterState: () => SavedRecipeFilterState | null;
  /**
   * Clear saved filter state
   */
  clearFilterState: () => void;
}

/**
 * Hook for persisting recipe filter state across navigation.
 *
 * Uses sessionStorage so state persists within a browser tab session
 * but resets when the tab is closed. Callers should save on every
 * filter/search/sort change (not just before navigating away) so state
 * survives any navigation path, not only back-navigation.
 *
 * @example
 * ```tsx
 * const { saveFilterState, loadFilterState, clearFilterState } = useRecipeFilterPersistence();
 *
 * // On mount - restore if available
 * const saved = loadFilterState();
 *
 * // Whenever filters/search/quickFilters/sort change
 * saveFilterState({ filters, searchTerm, activeQuickFilters, sortBy, sortDirection });
 *
 * // On explicit "Clear All"
 * clearFilterState();
 * ```
 */
export function useRecipeFilterPersistence(): UseRecipeFilterPersistenceReturn {
  const { userId } = useAuth();
  const storageKey = accountStorageKey(STORAGE_KEY, userId);
  const saveFilterState = useCallback(
    (state: Omit<SavedRecipeFilterState, "timestamp">) => {
      try {
        const toSave: SavedRecipeFilterState = {
          ...state,
          timestamp: Date.now(),
        };
        sessionStorage.setItem(storageKey, JSON.stringify(toSave));
      } catch (error) {
        console.error("[useRecipeFilterPersistence] Failed to save:", error);
      }
    },
    [storageKey]
  );

  const loadFilterState = useCallback((): SavedRecipeFilterState | null => {
    try {
      const stored = sessionStorage.getItem(storageKey);
      if (!stored) return null;

      const parsed = JSON.parse(stored) as SavedRecipeFilterState;

      // Check for staleness
      const age = Date.now() - parsed.timestamp;
      if (age > MAX_AGE_MS) {
        sessionStorage.removeItem(storageKey);
        return null;
      }

      return parsed;
    } catch (error) {
      console.error("[useRecipeFilterPersistence] Failed to load:", error);
      return null;
    }
  }, [storageKey]);

  const clearFilterState = useCallback(() => {
    try {
      sessionStorage.removeItem(storageKey);
    } catch (error) {
      console.error("[useRecipeFilterPersistence] Failed to clear:", error);
    }
  }, [storageKey]);

  return {
    saveFilterState,
    loadFilterState,
    clearFilterState,
  };
}
