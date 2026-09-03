"use client";

import { useRouter } from "next/navigation";
import { Users, Clock, Check, Bookmark } from "lucide-react";
import { formatTime } from "@/lib/quantityUtils";
import { cn, getErrorMessage } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RecipeImage } from "@/components/recipe/RecipeImage";
import { useMeal } from "@/hooks/api";
import { SideChip } from "./SideChip";
import { AISuggestions } from "./AISuggestions";
import { RecipeStats } from "./RecipeStats";
import type { RecipeCardDTO } from "@/types/recipe";

// ============================================================================
// TYPES
// ============================================================================

interface SelectedMealCardProps {
  /** The meal ID to fetch and display */
  mealId: number;
  /** Whether this meal entry is marked as completed */
  isCompleted?: boolean;
  /** Whether this meal is saved (persists after leaving planner) */
  isSaved?: boolean;
  /** Called when Mark Complete is clicked */
  onMarkComplete?: () => void;
  /** Called when Edit Meal is clicked */
  onEditMeal?: () => void;
  /** Called when Save is toggled */
  onToggleSave?: () => void;
  /** Called when Remove is clicked */
  onRemove?: () => void;
  /** Called when Add Side is clicked */
  onAddSide?: () => void;
  className?: string;
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

function SelectedMealSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("p-0 overflow-hidden", className)}>
      <div className="flex flex-col lg:flex-row">
        {/* Image skeleton */}
        <div className="w-full lg:w-64 h-48 lg:h-auto animate-pulse bg-muted flex-shrink-0" />

        {/* Content skeleton */}
        <div className="flex-1 p-6 space-y-4">
          <div className="h-8 w-2/3 animate-pulse bg-muted rounded" />
          <div className="h-4 w-1/3 animate-pulse bg-muted rounded" />
          <div className="flex gap-2">
            <div className="h-10 w-24 animate-pulse bg-muted rounded-lg" />
            <div className="h-10 w-24 animate-pulse bg-muted rounded-lg" />
          </div>
        </div>

        {/* Actions skeleton */}
        <div className="w-full lg:w-80 p-6 space-y-4 border-t lg:border-t-0 lg:border-l border-border">
          <div className="h-32 animate-pulse bg-muted rounded-xl" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-12 animate-pulse bg-muted rounded-lg" />
            <div className="h-12 animate-pulse bg-muted rounded-lg" />
            <div className="h-12 animate-pulse bg-muted rounded-lg" />
            <div className="h-12 animate-pulse bg-muted rounded-lg" />
          </div>
        </div>
      </div>
    </Card>
  );
}

// ============================================================================
// SELECTED MEAL CARD COMPONENT
// ============================================================================

export function SelectedMealCard({
  mealId,
  isCompleted = false,
  isSaved = false,
  onMarkComplete,
  onEditMeal,
  onToggleSave,
  onRemove,
  onAddSide,
  className,
}: SelectedMealCardProps) {
  const router = useRouter();
  const { data: meal, isLoading, error } = useMeal(mealId);

  // Navigate to recipe detail page
  const handleRecipeClick = (recipeId: number) => {
    router.push(`/recipes/${recipeId}`);
  };

  // Loading state
  if (isLoading) {
    return <SelectedMealSkeleton className={className} />;
  }

  // Error state
  if (error) {
    return (
      <Card className={cn("p-6 text-center", className)}>
        <p className="text-destructive font-medium">
          {getErrorMessage(error, "Failed to load meal")}
        </p>
      </Card>
    );
  }

  // No meal found
  if (!meal || !meal.main_recipe) {
    return (
      <Card className={cn("p-6 text-center", className)}>
        <p className="text-muted-foreground">Meal not found</p>
      </Card>
    );
  }

  const mainRecipe = meal.main_recipe;
  const sideRecipes = meal.side_recipes || [];

  return (
    <div className={cn("space-y-4", className)}>
      {/* Section Header */}
      <h2 className="text-lg font-semibold text-foreground">Selected Meal</h2>

      {/* Horizontal Card */}
      <Card className={cn("p-0 overflow-hidden", isCompleted && "opacity-60")}>
        <div className="flex flex-col lg:flex-row">
          {/* LEFT: Image Section */}
          <div
            className="group/image relative w-full lg:w-64 h-48 lg:h-auto flex-shrink-0 cursor-pointer overflow-hidden bg-elevated"
            onClick={() => handleRecipeClick(mainRecipe.id)}
          >
            {/* Transform wrapper - handles the zoom animation (matches MealGridCard) */}
            <div className="absolute inset-0 transition-transform duration-300 group-hover/image:scale-105">
              <RecipeImage
                src={mainRecipe.reference_image_path}
                alt={mainRecipe.recipe_name}
                fill
                className={cn(
                  "object-cover",
                  isCompleted && "grayscale"
                )}
                iconSize="xl"
                showLoadingState={false}
              />
            </div>
            {/* Completed Overlay */}
            {isCompleted && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                <Check className="h-12 w-12 text-success" strokeWidth={1.5} />
              </div>
            )}
          </div>

          {/* MIDDLE: Details Section */}
          <div className="flex-1 p-6 border-r border-border">
            {/* Title & Metadata */}
            <div className="mb-4">
              <h3
                className="text-2xl font-semibold text-foreground mb-2 cursor-pointer hover:text-primary transition-colors"
                onClick={() => handleRecipeClick(mainRecipe.id)}
              >
                {mainRecipe.recipe_name}
              </h3>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                {mainRecipe.servings != null && (
                  <span className="flex items-center gap-1.5">
                    <Users className="h-4 w-4" strokeWidth={1.5} />
                    {mainRecipe.servings} servings
                  </span>
                )}
                {mainRecipe.total_time != null && (
                  <span className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4" strokeWidth={1.5} />
                    {formatTime(mainRecipe.total_time)} total
                  </span>
                )}
              </div>
            </div>

            {/* Sides Section */}
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                Sides
              </h4>
              <div className="flex gap-2 flex-wrap">
                
                {/* 1. Render Existing Sides */}
                {sideRecipes.map((side: RecipeCardDTO) => (
                  <SideChip
                    key={side.id}
                    name={side.recipe_name}
                    category={side.recipe_category ?? undefined}
                    onClick={() => handleRecipeClick(side.id)}
                  />
                ))}

                {/* 2. Render "Add Side" Slot (if room exists) */}
                {!isCompleted && sideRecipes.length < 3 && (
                  <SideChip 
                    onClick={onAddSide} 
                    // No 'name' prop passed -> Renders as the "Add Side" dashed button automatically
                  />
                )}
                
              </div>
            </div>

            {/* AI Tip */}
            <AISuggestions
              mainRecipeName={mainRecipe.recipe_name}
              mainRecipeCategory={mainRecipe.recipe_category}
              mealType={mainRecipe.meal_type}
              mealId={meal.id}
            />
          </div>

          {/* RIGHT: Stats & Actions Section */}
          <div className="w-full lg:w-80 flex-shrink-0 p-6 space-y-4">
            {/* Recipe Stats */}
            <RecipeStats
              cookTime={meal.total_cook_time ?? null}
              servings={meal.avg_servings ?? null}
              timesCooked={meal.times_cooked ?? null}
              lastCooked={meal.last_cooked ?? null}
              dateAdded={meal.main_recipe?.created_at ?? null}
            />

            {/* Action Buttons */}
            {!isCompleted ? (
              <div className="grid grid-cols-2 gap-3">
                <Button onClick={onMarkComplete}>
                  Mark Complete
                </Button>
                <Button onClick={onEditMeal} variant="outline">
                  Edit Meal
                </Button>
                <Button
                  onClick={onToggleSave}
                  variant="outline"
                  className="gap-1.5"
                >
                  <Bookmark
                    className={cn(
                      "h-4 w-4",
                      isSaved && "fill-current text-primary"
                    )}
                    strokeWidth={1.5}
                  />
                  {isSaved ? "Saved" : "Save"}
                </Button>
                <Button
                  onClick={onRemove}
                  variant="outline"
                  className="border-destructive text-destructive"
                >
                  Remove
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-center gap-2 text-muted-foreground py-2">
                  <Check className="h-5 w-5 text-success" strokeWidth={1.5} />
                  <span className="text-sm">Completed</span>
                </div>
                <Button
                  onClick={onMarkComplete}
                  variant="outline"
                  className="w-full"
                >
                  Mark Incomplete
                </Button>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
