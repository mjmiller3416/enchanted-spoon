import { ChefHat, Plus, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecipeCard, RecipeCardGrid } from "@/components/recipe/RecipeCard";
import type { RecipeCardData } from "@/types/recipe";

export interface RecipeGridProps {
  recipes: RecipeCardData[];
  hasActiveFilters: boolean;
  onRecipeClick: (recipe: RecipeCardData) => void;
  onFavoriteToggle: (recipe: RecipeCardData) => void;
  onClearFilters: () => void;
  /** Empty-collection CTA: opens the recipe wizard (browse mode only) */
  onAddRecipe?: () => void;
  /** Empty-collection CTA: opens the Genie assistant (browse mode only) */
  onGenerateRecipe?: () => void;
  /** Select mode configuration */
  selectionMode?: boolean;
  selectedIds?: Set<string | number>;
}

export function RecipeGrid({
  recipes,
  hasActiveFilters,
  onRecipeClick,
  onFavoriteToggle,
  onClearFilters,
  onAddRecipe,
  onGenerateRecipe,
  selectionMode = false,
  selectedIds = new Set(),
}: RecipeGridProps) {
  if (recipes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="p-4 bg-elevated rounded-full mb-4">
          <ChefHat className="h-12 w-12 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          {hasActiveFilters ? "No Recipes Found" : "Start your collection"}
        </h3>
        <p className="text-sm text-muted-foreground max-w-sm mb-4">
          {hasActiveFilters
            ? "Try adjusting your filters or search term to find more recipes."
            : "Save your first recipe and it'll be ready to plan and shop from."}
        </p>
        {hasActiveFilters ? (
          <Button variant="outline" onClick={onClearFilters}>
            Clear All Filters
          </Button>
        ) : (
          (onAddRecipe || onGenerateRecipe) && (
            <div className="flex flex-col sm:flex-row items-center gap-3">
              {onAddRecipe && (
                <Button onClick={onAddRecipe}>
                  <Plus className="size-4" strokeWidth={1.5} />
                  Add your first recipe
                </Button>
              )}
              {onGenerateRecipe && (
                <Button variant="outline" onClick={onGenerateRecipe}>
                  <Sparkles className="size-4" strokeWidth={1.5} />
                  Generate with the Genie
                </Button>
              )}
            </div>
          )
        )}
      </div>
    );
  }

  return (
    <RecipeCardGrid size="medium">
      {recipes.map((recipe) => (
        <RecipeCard
          key={recipe.id}
          recipe={recipe}
          size="medium"
          onClick={onRecipeClick}
          onFavoriteToggle={onFavoriteToggle}
          isSelected={selectionMode && selectedIds.has(recipe.id)}
          selectionType={recipe.mealType === "side" ? "side" : "main"}
        />
      ))}
    </RecipeCardGrid>
  );
}
