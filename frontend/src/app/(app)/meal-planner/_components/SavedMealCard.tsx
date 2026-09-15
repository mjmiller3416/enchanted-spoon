"use client";

import { ChefHat } from "lucide-react";
import { Card } from "@/components/ui/card";
import { RecipeImage } from "@/components/recipe/RecipeImage";
import { getRecipeIcon } from "@/lib/recipeIcon";
import { RecipeIcon } from "@/components/common/RecipeIcon";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { MealSelectionResponseDTO } from "@/types/meal";

// ============================================================================
// TYPES
// ============================================================================

export interface SavedMealCardProps {
  /** The saved meal data to display */
  meal: MealSelectionResponseDTO;

  /** Called when the card is clicked */
  onSelect?: (meal: MealSelectionResponseDTO) => void;

  /** Whether this card is in a loading/adding state */
  isAdding?: boolean;

  /** Additional class names */
  className?: string;
}

// ============================================================================
// SAVED MEAL CARD COMPONENT
// ============================================================================

/**
 * SavedMealCard - Horizontal card showing a saved meal with side previews
 *
 * Features:
 * - Horizontal layout (image left, content right)
 * - Main dish image with hover zoom
 * - Meal name and main recipe name
 * - Side dish emoji row (using getRecipeEmoji)
 * - Stats: times cooked, last cooked
 * - Click to select action
 * - Disabled/loading state when isAdding
 */
export function SavedMealCard({
  meal,
  onSelect,
  isAdding = false,
  className,
}: SavedMealCardProps) {
  const sideRecipes = meal.side_recipes || [];
  const mainRecipe = meal.main_recipe;

  const handleClick = () => {
    if (!isAdding && onSelect) {
      onSelect(meal);
    }
  };

  return (
    <Card
      interactive
      onClick={handleClick}
      role="button"
      tabIndex={isAdding ? -1 : 0}
      aria-disabled={isAdding}
      aria-label={`Select ${meal.meal_name}`}
      onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); handleClick(); } }}
      className={cn(
        "overflow-hidden group p-0 gap-0 animate-slide-up focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        isAdding && "opacity-50 pointer-events-none",
        className
      )}
    >
      <div className="flex h-28">
        {/* Main dish image section */}
        <div className="relative w-28 h-28 bg-gradient-to-br from-hover to-elevated flex-shrink-0 overflow-hidden">
          {/* Image with hover zoom */}
          <div className="absolute inset-0 group-hover:scale-110 transition-transform duration-300">
            <RecipeImage
              src={mainRecipe?.reference_image_path ?? undefined}
              alt={meal.meal_name}
              fill
              iconSize="md"
              showLoadingState={false}
            />
          </div>
        </div>

        {/* Content section - flex column to distribute content */}
        <div className="flex-1 py-2 px-3 min-w-0 overflow-hidden flex flex-col">
          {/* Top: Meal name */}
          <h3 className="font-semibold text-foreground text-base truncate group-hover:text-primary transition-colors">
            {meal.meal_name}
          </h3>

          {/* Main recipe name - only show if different from meal name */}
          {mainRecipe && mainRecipe.recipe_name !== meal.meal_name && (
            <p className="text-sm text-muted-foreground truncate">
              {mainRecipe.recipe_name}
            </p>
          )}

          {/* Middle: Side dish icons - grows to fill available space */}
          <div className="flex-1 flex items-center gap-2">
            {sideRecipes.length > 0 ? (
              sideRecipes.map((side, i) => (
                <span
                  key={i}
                  title={side.recipe_name}
                >
                  <RecipeIcon
                    icon={getRecipeIcon(side.recipe_name, side.recipe_category ?? undefined)}
                    className="w-5 h-5"
                  />
                </span>
              ))
            ) : (
              <span className="text-xs text-muted-foreground/60">No sides</span>
            )}
          </div>

          {/* Bottom: Stats row - pushed to bottom by flex */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground/80 whitespace-nowrap">
            {meal.times_cooked !== null && meal.times_cooked > 0 && (
              <>
                <span className="flex items-center gap-1">
                  <ChefHat className="w-3.5 h-3.5" />
                  {meal.times_cooked}× cooked
                </span>
                {meal.last_cooked && <span>•</span>}
              </>
            )}
            {meal.last_cooked && (
              <span>{formatRelativeTime(meal.last_cooked)}</span>
            )}
            {!meal.times_cooked && !meal.last_cooked && (
              <span>Never cooked</span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
