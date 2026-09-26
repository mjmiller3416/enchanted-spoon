"use client";

import { useState, useEffect, useLayoutEffect, useCallback, useRef } from "react";
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
  /**
   * Compact mode for tight containers (the desktop detail pane): clamps the tip
   * to 2 lines with a More/Less toggle and drops the card's minimum height.
   * Off by default so other consumers keep the full card.
   */
  collapsible?: boolean;
  /**
   * With `collapsible`, start collapsed to just the header with a Show toggle
   * (used on short viewports). Ignored when `collapsible` is false.
   */
  defaultCollapsed?: boolean;
  className?: string;
}

// ============================================================================
// CACHE HELPERS (sessionStorage)
// ============================================================================

const CACHE_KEY_PREFIX = "ai-suggestions-";

// Keyed by the main dish too: editing a meal keeps its id, and a tip for the
// old dish must not be shown for the new one
function cacheKey(mealId: number, mainRecipeName: string): string {
  return `${CACHE_KEY_PREFIX}${mealId}:${mainRecipeName.trim().toLowerCase()}`;
}

function getCachedSuggestions(key: string): MealSuggestionsResponseDTO | null {
  try {
    if (typeof window === "undefined") return null;
    const cached = sessionStorage.getItem(key);
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
}

function setCachedSuggestions(key: string, data: MealSuggestionsResponseDTO): void {
  try {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(key, JSON.stringify(data));
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
  collapsible = false,
  defaultCollapsed = false,
  className,
}: AISuggestionsProps) {
  const [suggestions, setSuggestions] = useState<MealSuggestionsResponseDTO | null>(null);

  // Collapsible-mode UI state: body hidden behind the header, clamp expanded,
  // and whether the clamped tip actually overflows (only then offer More/Less)
  const [bodyHidden, setBodyHidden] = useState(collapsible && defaultCollapsed);
  const [expanded, setExpanded] = useState(false);
  const [isClamped, setIsClamped] = useState(false);
  const tipRef = useRef<HTMLParagraphElement>(null);

  // Use mutation hook with automatic token injection
  const suggestionsMutation = useMealSuggestions();
  const { mutate: mutateSuggestions, reset: resetSuggestions } = suggestionsMutation;
  const key = cacheKey(mealId, mainRecipeName);

  // Tips are generated only when asked for: each one spends the user's
  // monthly AI allowance, so merely opening a meal must never trigger one
  const fetchSuggestions = useCallback(() => {
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
            setCachedSuggestions(key, response);
          }
        },
      }
    );
  }, [key, mainRecipeName, mainRecipeCategory, mealType, mutateSuggestions]);

  // Show a tip already generated this session for this meal (no network).
  // Hydrating from sessionStorage after mount is the SSR-safe pattern.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSuggestions(getCachedSuggestions(key));
    resetSuggestions();
  }, [key, resetSuggestions]);

  const handleRegenerate = () => {
    fetchSuggestions();
  };

  const tipText = suggestions?.cooking_tip;

  // Measure whether the 2-line clamp hides text (re-checks on resize and when
  // the tip changes) so the More toggle only appears when there is more to see
  useLayoutEffect(() => {
    const el = tipRef.current;
    if (!collapsible || !el || expanded) return;
    const measure = () => setIsClamped(el.scrollHeight > el.clientHeight + 1);
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [collapsible, expanded, tipText, bodyHidden]);

  // Derive loading and error state from mutation
  const loading = suggestionsMutation.isPending;
  const error = suggestionsMutation.isError
    ? (suggestionsMutation.error instanceof Error ? suggestionsMutation.error.message : "Failed to get tip")
    : (!suggestionsMutation.isPending && suggestionsMutation.data && !suggestionsMutation.data.success)
      ? (suggestionsMutation.data.error || "Failed to get tip")
      : null;

  return (
    <Card
      className={cn(
        "bg-primary/10 border-primary/20",
        collapsible ? "p-3 gap-0" : "p-4 min-h-[120px]",
        className
      )}
    >
      {/* Header */}
      <div className={cn("flex items-center justify-between", !bodyHidden && (collapsible ? "mb-2" : "mb-3"))}>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-medium text-primary">Suggestion</h4>
        </div>
        <div className="flex items-center gap-1">
          {collapsible && (
            <Button
              variant="link"
              size="sm"
              className="h-6 px-1 text-xs text-primary/70 hover:text-primary"
              onClick={() => setBodyHidden((hidden) => !hidden)}
              aria-expanded={!bodyHidden}
            >
              {bodyHidden ? "Show" : "Hide"}
            </Button>
          )}
          {!bodyHidden && !loading && !error && (
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
      </div>

      {/* Loading State */}
      {!bodyHidden && loading && <AISuggestionsSkeleton />}

      {/* Error State */}
      {!bodyHidden && !loading && error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive/80">{error}</p>
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={() => fetchSuggestions()}
          >
            Try again
          </Button>
        </div>
      )}

      {/* Idle State: nothing generated yet for this meal */}
      {!bodyHidden && !loading && !error && !tipText && (
        <div className="space-y-2">
          <p className="text-sm text-primary/70">
            Get an AI cooking tip for this meal.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs"
            onClick={() => fetchSuggestions()}
          >
            <Sparkles className="h-3.5 w-3.5" strokeWidth={1.5} />
            Get a tip
          </Button>
        </div>
      )}

      {/* Success State */}
      {!bodyHidden && !loading && !error && tipText && (
        <>
          <p
            ref={tipRef}
            className={cn(
              "text-sm text-primary/70 leading-relaxed",
              collapsible && !expanded && "line-clamp-2"
            )}
          >
            {tipText}
          </p>
          {collapsible && (isClamped || expanded) && (
            <Button
              variant="link"
              size="sm"
              className="h-auto self-start p-0 mt-1 text-xs text-primary/70 hover:text-primary"
              onClick={() => setExpanded((prev) => !prev)}
              aria-expanded={expanded}
            >
              {expanded ? "Less" : "More"}
            </Button>
          )}
        </>
      )}
    </Card>
  );
}
