"use client";

import { cn } from "@/lib/utils";
import { getRecipeIcon } from "@/lib/recipeIcon";
import { RecipeIcon } from "@/components/common/RecipeIcon";
import { Separator } from "@/components/ui/separator";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link2 } from "lucide-react";

interface RecipeInfo {
  name: string;
  itemCount: number;
  collectedCount: number;
  isFirstInMeal?: boolean; // True if this recipe starts a new meal grouping
  isDuplicate?: boolean; // True if this recipe appears in multiple meals
  instanceKey: string; // Unique key per meal instance (e.g., "meal-5-Air Fryer Potatoes")
}

interface IngredientSourceSidebarProps {
  recipes: RecipeInfo[];
  manualItemCount: number;
  manualCollectedCount: number;
  activeFilter: string | null;
  onFilterChange: (recipeName: string | null) => void;
}

/**
 * IngredientSourceSidebar - Filter shopping list items by their source
 *
 * Shows recipes contributing ingredients to the shopping list.
 * Click to filter shopping list by recipe source.
 *
 * Features:
 * - Lists all recipes with item counts and progress
 * - Click to filter shopping list by recipe
 * - Manual items section at the bottom
 * - Sticky positioning for scroll behavior
 */
export function IngredientSourceSidebar({
  recipes,
  manualItemCount,
  manualCollectedCount,
  activeFilter,
  onFilterChange,
}: IngredientSourceSidebarProps) {
  const handleRecipeClick = (recipeName: string) => {
    // Toggle filter off if clicking the same recipe
    onFilterChange(activeFilter === recipeName ? null : recipeName);
  };

  const handleManualClick = () => {
    onFilterChange(activeFilter === "__manual__" ? null : "__manual__");
  };

  // Don't render if no recipes and no manual items
  if (recipes.length === 0 && manualItemCount === 0) {
    return null;
  }

  return (
    <Card className="p-4 flex flex-col min-h-0">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex-shrink-0">
          Recipes in this list
        </h2>

        <div className="flex flex-col gap-2 overflow-y-auto overflow-x-hidden flex-1 px-1 -mx-1 pb-0.5">
          {recipes.map((recipe, index) => {
            const isActive = activeFilter === recipe.name;
            const icon = getRecipeIcon(recipe.name);
            // Show separator before new meal groups (but not the first one)
            const showSeparator = recipe.isFirstInMeal && index > 0;

            return (
              <div key={recipe.instanceKey}>
                {showSeparator && <Separator className="my-2" />}
                <Button
                  variant="ghost"
                  onClick={() => handleRecipeClick(recipe.name)}
                  className={cn(
                    "flex items-center gap-3 p-3 h-auto w-full justify-start bg-accent transition-all hover:scale-[1.02] hover:bg-accent dark:hover:bg-accent",
                    isActive && "bg-primary/15 border border-primary/50"
                  )}
                >
                  {/* Recipe icon */}
                  <RecipeIcon icon={icon} className="w-5 h-5 flex-shrink-0" />

                  {/* Recipe info */}
                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn(
                          "font-medium text-sm truncate",
                          isActive ? "text-primary" : "text-foreground"
                        )}
                      >
                        {recipe.name}
                      </span>
                      {recipe.isDuplicate && (
                        <Link2 className="w-3 h-3 flex-shrink-0 text-primary" strokeWidth={1.5} />
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground font-normal">
                      {recipe.collectedCount}/{recipe.itemCount} items
                    </div>
                  </div>
                </Button>
              </div>
            );
          })}

          {/* Manual items section */}
          {manualItemCount > 0 && (
            <>
              {recipes.length > 0 && (
                <Separator className="my-2" />
              )}
              <Button
                variant="ghost"
                onClick={handleManualClick}
                className={cn(
                  "flex items-center gap-3 p-3 h-auto w-full justify-start bg-accent transition-all hover:scale-[1.02] hover:bg-accent dark:hover:bg-accent",
                  activeFilter === "__manual__" && "bg-secondary/15 border border-secondary/50"
                )}
              >
                {/* Manual emoji */}
                <span className="text-xl flex-shrink-0">✏️</span>

                {/* Manual info */}
                <div className="flex-1 min-w-0 text-left">
                  <div
                    className={cn(
                      "font-medium text-sm",
                      activeFilter === "__manual__"
                        ? "text-secondary"
                        : "text-foreground"
                    )}
                  >
                    Manual items
                  </div>
                  <div className="text-xs text-muted-foreground font-normal">
                    {manualCollectedCount}/{manualItemCount} items
                  </div>
                </div>
              </Button>
            </>
          )}
        </div>
    </Card>
  );
}

// Backward compatibility alias
export const RecipeFilterSidebar = IngredientSourceSidebar;
