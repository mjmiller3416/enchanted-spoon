import { useRef, useState } from "react";
import { ChefHat, Plus, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecipeCard, RecipeCardGrid } from "@/components/recipe/RecipeCard";
import type { RecipeCardData } from "@/types/recipe";

export interface RecipeGridProps {
  recipes: RecipeCardData[];
  page?: number;
  onPageChange?: (page: number) => void;
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
  page: requestedPage,
  onPageChange,
  hasActiveFilters,
  onRecipeClick,
  onFavoriteToggle,
  onClearFilters,
  onAddRecipe,
  onGenerateRecipe,
  selectionMode = false,
  selectedIds = new Set(),
}: RecipeGridProps) {
  const [localPage, setPage] = useState(0);
  const gridRef = useRef<HTMLDivElement>(null);
  const pageSize = 24;
  const pages = Math.ceil(recipes.length / pageSize);
  const rawPage = requestedPage ?? localPage;
  const page = Math.min(Math.max(0, Number.isInteger(rawPage) ? rawPage : 0), Math.max(0, pages - 1));
  const changePage = (next: number) => { setPage(next); onPageChange?.(next); gridRef.current?.scrollIntoView({ block: "start" }); };
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
    <div ref={gridRef} className="scroll-mt-24">
    <p className="mb-4 text-sm text-muted-foreground" role="status">{recipes.length} {recipes.length === 1 ? "recipe" : "recipes"}{pages > 1 && ` · Page ${page + 1} of ${pages}`}</p>
    <RecipeCardGrid size="medium">
      {recipes.slice(page * pageSize, (page + 1) * pageSize).map((recipe) => (
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
    {pages > 1 && <nav aria-label="Recipe pages" className="mt-6 flex items-center justify-center gap-4">
      <Button variant="outline" disabled={page === 0} onClick={() => changePage(page - 1)}>Previous</Button>
      <span className="text-sm text-muted-foreground">{page + 1} / {pages}</span>
      <Button variant="outline" disabled={page + 1 === pages} onClick={() => changePage(page + 1)}>Next</Button>
    </nav>}
    </div>
  );
}
