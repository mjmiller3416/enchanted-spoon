"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useMealSuggestions } from "@/hooks/api";
import type { MealSuggestionsResponseDTO } from "@/types/ai";

// ============================================================================
// TYPES
// ============================================================================

interface AISuggestionsProps {
  mainRecipeName: string;
  mainRecipeCategory?: string | null;
  mealType?: string | null;
  mealId: number;
  className?: string;
}

// ============================================================================
// CACHE HELPERS (sessionStorage)
// ============================================================================

const CACHE_KEY_PREFIX = "ai-suggestions-";

function getCachedSuggestions(mealId: number): MealSuggestionsResponseDTO | null {
  try {
    if (typeof window === "undefined") return null;
    const cached = sessionStorage.getItem(`${CACHE_KEY_PREFIX}${mealId}`);
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
}

function setCachedSuggestions(mealId: number, data: MealSuggestionsResponseDTO): void {
  try {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(`${CACHE_KEY_PREFIX}${mealId}`, JSON.stringify(data));
  } catch {
    // Ignore storage errors
  }
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

function AISuggestionsSkeleton() {
  return (
    <div className="flex items-start gap-3">
      <div className="h-4 w-4 rounded bg-primary/20 animate-pulse flex-shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 w-full rounded bg-primary/20 animate-pulse" />
        <div className="h-3 w-3/4 rounded bg-primary/20 animate-pulse" />
      </div>
    </div>
  );
}

// ============================================================================
// AI SUGGESTIONS COMPONENT
// ============================================================================

export function AISuggestions({
  mainRecipeName,
  mainRecipeCategory,
  mealType,
  mealId,
  className,
}: AISuggestionsProps) {
  const [suggestions, setSuggestions] = useState<MealSuggestionsResponseDTO | null>(null);

  // Use mutation hook with automatic token injection
  const suggestionsMutation = useMealSuggestions();
  const { mutate: mutateSuggestions } = suggestionsMutation;

  // Track which mealId we've already fetched to prevent duplicate requests
  const fetchedMealIdRef = useRef<number | null>(null);

  const fetchSuggestions = useCallback(async (forceRefresh = false) => {
    // Prevent duplicate fetches for same mealId (unless force refresh)
    if (!forceRefresh && fetchedMealIdRef.current === mealId) {
      return;
    }

    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cached = getCachedSuggestions(mealId);
      if (cached) {
        setSuggestions(cached);
        fetchedMealIdRef.current = mealId;
        return;
      }
    }

    mutateSuggestions(
      {
        main_recipe_name: mainRecipeName,
        main_recipe_category: mainRecipeCategory || undefined,
        meal_type: mealType || undefined,
      },
      {
        onSuccess: (response) => {
          if (response.success) {
            setSuggestions(response);
            setCachedSuggestions(mealId, response);
            fetchedMealIdRef.current = mealId; // Mark as fetched only on success
          }
        },
        onError: () => {
          // Reset ref on error to allow retry
          fetchedMealIdRef.current = null;
        },
      }
    );
  }, [mealId, mainRecipeName, mainRecipeCategory, mealType, mutateSuggestions]);

  // Auto-load on mount or when mealId changes. The cache-hit path inside
  // fetchSuggestions hydrates state synchronously from sessionStorage — that
  // post-mount hydration is the SSR-safe pattern for external stores.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleRegenerate = () => {
    fetchSuggestions(true);
  };

  // Derive loading and error state from mutation
  const loading = suggestionsMutation.isPending;
  const error = suggestionsMutation.isError
    ? (suggestionsMutation.error instanceof Error ? suggestionsMutation.error.message : "Failed to get tip")
    : (!suggestionsMutation.isPending && suggestionsMutation.data && !suggestionsMutation.data.success)
      ? (suggestionsMutation.data.error || "Failed to get tip")
      : null;

  return (
    <Card className={cn("p-4 bg-primary/10 border-primary/20 min-h-[120px]", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-medium text-primary">Suggestion</h4>
        </div>
        {!loading && !error && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-primary/70 hover:text-primary hover:bg-primary/10"
            onClick={handleRegenerate}
            title="Get new tip"
            aria-label="Get new tip"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Loading State */}
      {loading && <AISuggestionsSkeleton />}

      {/* Error State */}
      {!loading && error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive/80">{error}</p>
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={() => fetchSuggestions(true)}
          >
            Try again
          </Button>
        </div>
      )}

      {/* Success State */}
      {!loading && !error && suggestions?.cooking_tip && (
        <p className="text-sm text-primary/70 leading-relaxed">
          {suggestions.cooking_tip}
        </p>
      )}
    </Card>
  );
}
