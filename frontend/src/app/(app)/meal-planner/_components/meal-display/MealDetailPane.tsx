"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  Calendar,
  Check,
  CheckCircle,
  Clock,
  Loader2,
  Pencil,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { formatTime } from "@/lib/quantityUtils";
import { cn, formatRelativeTime, getErrorMessage } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RecipeImage } from "@/components/recipe/RecipeImage";
import { useMeal } from "@/hooks/api";
import { useMediaQuery } from "@/hooks/ui/useMediaQuery";
import { SideChip } from "./SideChip";
import { AISuggestions } from "./AISuggestions";
import type { MealSelectionResponseDTO } from "@/types/meal";
import type { RecipeCardDTO } from "@/types/recipe";

/** Mirrors the `short` custom variant in globals.css */
const SHORT_VIEWPORT_QUERY = "(max-height: 42rem)";

// ============================================================================
// TYPES
// ============================================================================

interface MealDetailPaneProps {
  /** Meal to fetch and display */
  mealId: number;
  /** Meal name from the planner entry — shown immediately while the meal loads */
  mealName: string;
  /** Whether this planner entry is marked as completed */
  isCompleted: boolean;
  /** Whether this meal is saved (persists after leaving the menu) */
  isSaved: boolean;
  /** Bump to remount the body and pick up refreshed meal stats */
  refreshKey: number;
  /** Mark Complete / Mark Incomplete is in flight */
  isCompletePending?: boolean;
  /** Save toggle is in flight */
  isSavePending?: boolean;
  /** Edit meal data is being fetched before the builder opens */
  isEditLoading?: boolean;
  /** Close the pane (X button; Esc is handled by the page) */
  onClose: () => void;
  /** Toggle completion for this entry */
  onMarkComplete: () => void;
  /** Open the meal builder in edit mode */
  onEditMeal: () => void;
  /** Toggle the meal's saved status */
  onToggleSave: () => void;
  /** Remove this entry from the menu */
  onRemove: () => void;
  /** Open the meal builder to add a side */
  onAddSide: () => void;
}

// ============================================================================
// STAT CHIPS
// ============================================================================

interface MealStatChipsProps {
  meal: MealSelectionResponseDTO;
}

/**
 * One row of small meal-level stat chips (total time, servings, cook history)
 * — the compact replacement for the RecipeStats card inside the pane.
 */
function MealStatChips({ meal }: MealStatChipsProps) {
  const timesCooked = meal.times_cooked ?? 0;

  return (
    <ul className="flex flex-wrap gap-2" aria-label="Meal stats">
      {meal.total_cook_time != null && (
        <li>
          <Badge variant="plain" className="bg-muted text-muted-foreground">
            <Clock strokeWidth={1.5} />
            {formatTime(meal.total_cook_time)}
          </Badge>
        </li>
      )}
      {meal.avg_servings != null && (
        <li>
          <Badge variant="plain" className="bg-muted text-muted-foreground">
            <Users strokeWidth={1.5} />
            {Math.round(meal.avg_servings)} servings
          </Badge>
        </li>
      )}
      {timesCooked > 0 ? (
        <>
          <li>
            <Badge variant="plain" className="bg-muted text-muted-foreground">
              <CheckCircle strokeWidth={1.5} />
              Cooked {timesCooked}×
            </Badge>
          </li>
          {meal.last_cooked && (
            <li>
              <Badge variant="plain" className="bg-muted text-muted-foreground">
                <Calendar strokeWidth={1.5} />
                Last {formatRelativeTime(meal.last_cooked)}
              </Badge>
            </li>
          )}
        </>
      ) : (
        <li>
          <Badge variant="plain" className="bg-muted text-muted-foreground">
            <CheckCircle strokeWidth={1.5} />
            Not cooked yet
          </Badge>
        </li>
      )}
    </ul>
  );
}

// ============================================================================
// BODY (scrolling middle region)
// ============================================================================

interface MealDetailBodyProps {
  mealId: number;
  isCompleted: boolean;
  onAddSide: () => void;
}

/** Placeholder matching the body layout while the meal loads */
function MealDetailBodySkeleton() {
  return (
    <div className="space-y-5" aria-hidden="true">
      <Skeleton className="w-full aspect-21/9 short:hidden rounded-lg" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-24" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-3 w-12" />
        <div className="flex gap-2">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-28" />
        </div>
      </div>
      <Skeleton className="h-20 w-full rounded-xl" />
    </div>
  );
}

/**
 * Fetches the meal and renders the pane's scrolling content: main recipe
 * banner (a thumbnail beside the stats on short viewports), stat chips,
 * sides, and the collapsible AI suggestion.
 */
function MealDetailBody({ mealId, isCompleted, onAddSide }: MealDetailBodyProps) {
  const router = useRouter();
  const { data: meal, isLoading, error } = useMeal(mealId);
  const isShortViewport = useMediaQuery(SHORT_VIEWPORT_QUERY);

  // Navigate to recipe detail page
  const handleRecipeClick = (recipeId: number) => {
    router.push(`/recipes/${recipeId}`);
  };

  if (isLoading) return <MealDetailBodySkeleton />;

  if (error) {
    return (
      <p className="text-sm text-destructive font-medium">
        {getErrorMessage(error, "Failed to load meal")}
      </p>
    );
  }

  if (!meal || !meal.main_recipe) {
    return <p className="text-sm text-muted-foreground">Meal not found</p>;
  }

  const mainRecipe = meal.main_recipe;
  const sideRecipes = meal.side_recipes || [];

  return (
    <div className="space-y-5">
      {/* Main recipe banner + stats (thumbnail beside the chips on short screens) */}
      <div className="flex flex-col gap-4 short:flex-row short:items-center">
        <Button
          variant="ghost"
          aria-label={`View ${mainRecipe.recipe_name}`}
          className="group/image relative w-full aspect-21/9 h-auto short:size-16 short:aspect-square p-0 shrink-0 overflow-hidden rounded-lg bg-elevated"
          onClick={() => handleRecipeClick(mainRecipe.id)}
        >
          {/* Transform wrapper - handles the zoom animation (matches MealGridCard) */}
          <div className="absolute inset-0 transition-transform duration-300 group-hover/image:scale-105 motion-reduce:transition-none">
            <RecipeImage
              src={mainRecipe.banner_image_path ?? mainRecipe.reference_image_path}
              alt={mainRecipe.recipe_name}
              fill
              className={cn("object-cover", isCompleted && "grayscale")}
              iconSize="xl"
              showLoadingState={false}
            />
          </div>
          {isCompleted && (
            <div className="absolute inset-0 flex items-center justify-center bg-background-intense/40">
              <Check className="size-10 short:size-6 text-success" strokeWidth={1.5} />
            </div>
          )}
        </Button>

        <MealStatChips meal={meal} />
      </div>

      {/* Sides */}
      <section aria-labelledby="meal-detail-sides">
        <h3
          id="meal-detail-sides"
          className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3"
        >
          Sides
        </h3>
        <div className="flex gap-2 flex-wrap">
          {sideRecipes.map((side: RecipeCardDTO) => (
            <SideChip
              key={side.id}
              name={side.recipe_name}
              category={side.recipe_category ?? undefined}
              onClick={() => handleRecipeClick(side.id)}
            />
          ))}
          {/* Empty "Add Side" slot while there's room (no name → dashed variant) */}
          {!isCompleted && sideRecipes.length < 3 && <SideChip onClick={onAddSide} />}
          {isCompleted && sideRecipes.length === 0 && (
            <p className="text-sm text-muted-foreground">No sides</p>
          )}
        </div>
      </section>

      {/* AI tip — clamped in the pane; header-only to start on short screens */}
      <AISuggestions
        mainRecipeName={mainRecipe.recipe_name}
        mainRecipeCategory={mainRecipe.recipe_category}
        mealType={mainRecipe.meal_type}
        mealId={meal.id}
        collapsible
        defaultCollapsed={isShortViewport}
      />
    </div>
  );
}

// ============================================================================
// MEAL DETAIL PANE
// ============================================================================

/**
 * MealDetailPane - integrated desktop (lg+) detail pane for the open menu meal.
 *
 * Docked flush to the right edge beside the page (not an overlay): sticky
 * below the TopNav at full remaining viewport height via the `detail-pane`
 * utility, separated from the grid by a single left divider and a subtle
 * tonal shift — deliberately no card treatment, so it reads as the selected
 * meal rather than a popup.
 *
 * The shell stays mounted while a meal is open, so the entrance animation
 * plays once; switching meals only swaps the keyed body. Header and footer
 * are pinned; only the middle region scrolls. Focus moves to the heading when
 * the pane first opens (returning focus on close is the page's job).
 */
export function MealDetailPane({
  mealId,
  mealName,
  isCompleted,
  isSaved,
  refreshKey,
  isCompletePending = false,
  isSavePending = false,
  isEditLoading = false,
  onClose,
  onMarkComplete,
  onEditMeal,
  onToggleSave,
  onRemove,
  onAddSide,
}: MealDetailPaneProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Move focus into the pane on first open only — swapping meals keeps focus
  // where the user is (usually the grid)
  useEffect(() => {
    headingRef.current?.focus({ preventScroll: true });
  }, []);

  return (
    <aside
      aria-labelledby="meal-detail-heading"
      className="detail-pane w-120 shrink-0 border-l border-border-subtle bg-background-subtle"
    >
      {/* Pinned header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b border-border-subtle">
        <h2
          id="meal-detail-heading"
          ref={headingRef}
          tabIndex={-1}
          title={mealName}
          className="flex-1 min-w-0 truncate text-section-header focus-visible:outline-none"
        >
          {mealName}
        </h2>
        <Button variant="ghost" size="icon" aria-label="Close meal details" onClick={onClose}>
          <X className="size-5" strokeWidth={1.5} />
        </Button>
      </div>

      {/* Scrolling middle — keyed so a new meal (or refreshed stats) swaps content */}
      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-5">
        <MealDetailBody
          key={`${mealId}-${refreshKey}`}
          mealId={mealId}
          isCompleted={isCompleted}
          onAddSide={onAddSide}
        />
      </div>

      {/* Pinned footer */}
      <div className="flex items-center gap-2 px-6 py-4 border-t border-border-subtle">
        {!isCompleted ? (
          <>
            <Button className="flex-1" onClick={onMarkComplete} disabled={isCompletePending}>
              {isCompletePending ? (
                <Loader2 className="animate-spin" strokeWidth={1.5} />
              ) : (
                <Check strokeWidth={1.5} />
              )}
              Mark Complete
            </Button>
            <Button variant="outline" onClick={onEditMeal} disabled={isEditLoading}>
              {isEditLoading ? (
                <Loader2 className="animate-spin" strokeWidth={1.5} />
              ) : (
                <Pencil strokeWidth={1.5} />
              )}
              Edit
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Save meal"
              aria-pressed={isSaved}
              onClick={onToggleSave}
              disabled={isSavePending}
            >
              <Bookmark
                className={cn(isSaved && "fill-current text-primary")}
                strokeWidth={1.5}
              />
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Remove from menu"
              className="border-destructive text-destructive hover:border-destructive hover:bg-destructive/10"
              onClick={onRemove}
            >
              <Trash2 strokeWidth={1.5} />
            </Button>
          </>
        ) : (
          <>
            <span className="flex flex-1 items-center gap-2 text-sm text-muted-foreground">
              <Check className="size-5 text-success" strokeWidth={1.5} />
              Completed
            </span>
            <Button variant="outline" onClick={onMarkComplete} disabled={isCompletePending}>
              {isCompletePending && <Loader2 className="animate-spin" strokeWidth={1.5} />}
              Mark Incomplete
            </Button>
          </>
        )}
      </div>
    </aside>
  );
}
