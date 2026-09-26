"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { recipeApi } from "@/lib/api";
import { recipeQueryKeys, plannerQueryKeys, dashboardQueryKeys } from "./queryKeys";
import { dispatchRecipeUpdate } from "./events";
import { invalidateRecipeDependents } from "./invalidateRecipeDependents";
import type {
  RecipeResponseDTO,
  RecipeCardDTO,
  RecipeFilterDTO,
  RecipeCreateDTO,
  RecipeUpdateDTO,
} from "@/types/recipe";

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch all recipes with optional filters.
 * Returns full recipe data (including ingredients).
 */
export function useRecipes(filters?: Partial<RecipeFilterDTO>) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeQueryKeys.list(filters),
    queryFn: async () => {
      const token = await getToken();
      return recipeApi.list(filters, token);
    },
    staleTime: 30000, // 30 seconds - recipes don't change that frequently
  });
}

/**
 * Fetch recipes as lightweight cards.
 * Ideal for lists and grids where full recipe data isn't needed.
 */
export function useRecipeCards(filters?: {
  recipe_category?: string;
  meal_type?: string;
  favorites_only?: boolean;
  search_term?: string;
  limit?: number;
}) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeQueryKeys.cards(filters),
    queryFn: async () => {
      const token = await getToken();
      return recipeApi.listCards(filters, token);
    },
    staleTime: 30000,
  });
}

/**
 * Fetch a single recipe by ID with full details.
 * Includes ingredients, directions, notes, etc.
 */
export function useRecipe(recipeId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeQueryKeys.detail(recipeId!),
    queryFn: async () => {
      const token = await getToken();
      return recipeApi.get(recipeId!, token);
    },
    enabled: recipeId !== null,
    staleTime: 60000, // 1 minute - single recipe data is less volatile
  });
}

/**
 * Fetch all unique recipe categories.
 * Used for filter dropdowns and category management.
 */
export function useRecipeCategories() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeQueryKeys.categories(),
    queryFn: async () => {
      const token = await getToken();
      return recipeApi.getCategories(token);
    },
    staleTime: 300000, // 5 minutes - categories change rarely
  });
}

/**
 * Fetch all unique meal types.
 * Used for filter dropdowns.
 */
export function useRecipeMealTypes() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeQueryKeys.mealTypes(),
    queryFn: async () => {
      const token = await getToken();
      return recipeApi.getMealTypes(token);
    },
    staleTime: 300000, // 5 minutes
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Create a new recipe.
 * Invalidates recipe lists on success.
 */
export function useCreateRecipe() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RecipeCreateDTO) => {
      const token = await getToken();
      return recipeApi.create(data, token);
    },
    onSuccess: () => {
      // Invalidate all recipe lists to include the new recipe
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.all });
      // Recipe count feeds the Home header chips and first-run flow
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stats() });
      dispatchRecipeUpdate();
    },
  });
}

/**
 * Update an existing recipe.
 * Invalidates recipe lists and the specific recipe detail.
 */
export function useUpdateRecipe() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ recipeId, data }: { recipeId: number; data: RecipeUpdateDTO }) => {
      const token = await getToken();
      return recipeApi.update(recipeId, data, token);
    },
    onSuccess: (updatedRecipe) => {
      // Update the specific recipe in cache
      queryClient.setQueryData(
        recipeQueryKeys.detail(updatedRecipe.id),
        updatedRecipe
      );
      // Invalidate lists as name/category may have changed
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.list() });
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.cards() });
      // Invalidate planner entries as they may reference this recipe
      void invalidateRecipeDependents(queryClient);
      dispatchRecipeUpdate();
    },
  });
}

/**
 * Delete a recipe.
 * Invalidates all recipe caches and planner entries.
 */
export function useDeleteRecipe() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (recipeId: number) => {
      const token = await getToken();
      return recipeApi.delete(recipeId, token);
    },
    onSuccess: (_data, recipeId) => {
      // Remove the specific recipe from cache
      queryClient.removeQueries({ queryKey: recipeQueryKeys.detail(recipeId) });
      // Invalidate all lists
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.list() });
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.cards() });
      // Invalidate planner entries as meals may reference this recipe
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.entries() });
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stats() });
      dispatchRecipeUpdate();
    },
  });
}

/**
 * Toggle a recipe's favorite status.
 * With optimistic update for instant UI feedback.
 */
export function useToggleFavorite() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { errorMessage: "Couldn't update favorite" },
    scope: { id: "recipe-favorites" },
    mutationFn: async (recipeId: number) => {
      const token = await getToken();
      return recipeApi.toggleFavorite(recipeId, token);
    },
    onSuccess: (recipe) => {
      queryClient.setQueryData(recipeQueryKeys.detail(recipe.id), recipe);
      queryClient.setQueriesData<RecipeResponseDTO[]>({ queryKey: recipeQueryKeys.list() },
        old => old?.map(item => item.id === recipe.id ? { ...item, is_favorite: recipe.is_favorite } : item));
      queryClient.setQueriesData<RecipeCardDTO[]>({ queryKey: recipeQueryKeys.cards() },
        old => old?.map(item => item.id === recipe.id ? { ...item, is_favorite: recipe.is_favorite } : item));
    },
    onSettled: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.all }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.all }),
    ]),
  });
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Manually refresh all recipe lists.
 * Useful for event-based refresh patterns.
 */
export function useRefreshRecipes() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: recipeQueryKeys.all });
  };
}

/**
 * Prefetch a recipe by ID.
 * Useful for hover-to-prefetch patterns.
 */
export function usePrefetchRecipe() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return async (recipeId: number) => {
    await queryClient.prefetchQuery({
      queryKey: recipeQueryKeys.detail(recipeId),
      queryFn: async () => {
        const token = await getToken();
        return recipeApi.get(recipeId, token);
      },
      staleTime: 60000,
    });
  };
}
