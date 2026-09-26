"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useRecipe, useDeleteRecipe, usePlannerEntries, useToggleFavorite } from "@/hooks/api";
import { toast } from "sonner";
import type { RecipeResponseDTO } from "@/types/recipe";
import { useRecentRecipes } from "@/hooks/persistence";
import { parseDirections, groupIngredientsByCategory } from "./recipe-utils";

/**
 * Custom hook for managing recipe detail view state and logic.
 * Handles data fetching, favorites, ingredient/step progress, and CRUD operations.
 * Now uses centralized React Query hooks for data fetching.
 */
export function useRecipeView(recipeId: number) {
  const router = useRouter();
  const { addToRecent } = useRecentRecipes();

  // Fetch recipe and planner entries via React Query
  const { data: recipe, isLoading: recipeLoading, error, refetch, isFetching } = useRecipe(recipeId);
  const { data: plannerEntries = [] } = usePlannerEntries();
  const deleteRecipeMutation = useDeleteRecipe();
  const favoriteMutation = useToggleFavorite();

  // Local state for UI interactions. Favorite is derived from the recipe with
  // a local override so toggling doesn't require mirroring server state.
  const [checkedIngredients, setCheckedIngredients] = useState<Set<number>>(new Set());
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  const loading = recipeLoading;
  const isFavorite = recipe?.is_favorite ?? false;

  // Track this recipe as recently viewed once it loads
  useEffect(() => {
    if (recipe) {
      addToRecent({
        id: recipe.id,
        name: recipe.recipe_name,
        category: recipe.recipe_category || undefined,
      });
    }
  }, [recipe, addToRecent]);

  // Parse directions
  const directions = useMemo(() => {
    return parseDirections(recipe?.directions || null);
  }, [recipe?.directions]);

  // Group ingredients
  const ingredients = recipe?.ingredients;
  const groupedIngredients = useMemo(() => {
    if (!ingredients) return new Map<string, RecipeResponseDTO["ingredients"]>();
    return groupIngredientsByCategory(ingredients);
  }, [ingredients]);

  // Handlers
  const handleFavoriteToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (favoriteMutation.isPending) return;
    favoriteMutation.mutate(recipeId, {
      onError: () => toast.error("Couldn't update favorite. Please try again."),
    });
  };

  const handleIngredientToggle = (ingredientId: number) => {
    setCheckedIngredients(prev => {
      const next = new Set(prev);
      if (next.has(ingredientId)) {
        next.delete(ingredientId);
      } else {
        next.add(ingredientId);
      }
      return next;
    });
  };

  const handleStepToggle = (stepIndex: number) => {
    setCompletedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepIndex)) {
        next.delete(stepIndex);
      } else {
        next.add(stepIndex);
      }
      return next;
    });
  };

  const handleDelete = async () => {
    try {
      await deleteRecipeMutation.mutateAsync(recipeId);
      router.push("/recipes");
    } catch (error) {
      console.error("Failed to delete recipe:", error);
      toast.error("Couldn't delete the recipe. Please try again.");
      throw error;
    }
  };

  const handleMealAdded = async () => {
    // Planner entries are automatically refreshed by React Query
    // when mutations invalidate the cache - no manual refresh needed
  };

  // Progress calculations
  const ingredientProgress = recipe?.ingredients.length
    ? Math.round((checkedIngredients.size / recipe.ingredients.length) * 100)
    : 0;
  const stepProgress = directions.length
    ? Math.round((completedSteps.size / directions.length) * 100)
    : 0;

  return {
    // Data
    recipe: recipe ?? null,
    error,
    refetch,
    isFetching,
    loading,
    isFavorite,
    favoritePending: favoriteMutation.isPending,
    plannerEntries,
    directions,
    groupedIngredients,

    // Progress state
    checkedIngredients,
    completedSteps,
    ingredientProgress,
    stepProgress,

    // Handlers
    handleFavoriteToggle,
    handleIngredientToggle,
    handleStepToggle,
    handleDelete,
    handleMealAdded,
  };
}
