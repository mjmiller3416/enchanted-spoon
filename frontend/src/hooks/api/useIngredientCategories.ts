"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { ingredientCategoryApi } from "@/lib/api";
import type {
  UserIngredientCategoryDTO,
  UserIngredientCategoryCreateDTO,
  UserIngredientCategoryUpdateDTO,
  UserIngredientCategoryReorderDTO,
  UserIngredientCategoryBulkUpdateDTO,
  IngredientCategoryOption,
} from "@/types/ingredient-settings";

// ============================================================================
// QUERY KEYS
// ============================================================================

export const ingredientCategoryQueryKeys = {
  all: ["ingredient-categories"] as const,
  lists: () => [...ingredientCategoryQueryKeys.all, "list"] as const,
  list: (includeDisabled?: boolean) =>
    [...ingredientCategoryQueryKeys.lists(), { includeDisabled }] as const,
  details: () => [...ingredientCategoryQueryKeys.all, "detail"] as const,
  detail: (id: number) =>
    [...ingredientCategoryQueryKeys.details(), id] as const,
};

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch all ingredient categories for the current user.
 * Returns categories ordered by position.
 * On first access, built-in categories are automatically seeded.
 */
export function useIngredientCategories(includeDisabled = false) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: ingredientCategoryQueryKeys.list(includeDisabled),
    queryFn: async () => {
      const token = await getToken();
      return ingredientCategoryApi.list(token, includeDisabled);
    },
    staleTime: 30000,
  });
}

/**
 * Convenience hook: Get ingredient categories formatted as dropdown options.
 *
 * Returns:
 * - options: Categories as { value, label } for form dropdowns
 * - categories: Raw category data
 * - isLoading: Loading state
 * - error: Error state
 *
 * This hook replaces the static INGREDIENT_CATEGORIES constant.
 */
export function useIngredientCategoryOptions() {
  const { data: categories = [], isLoading, error } = useIngredientCategories(false);

  // Memoize so the options reference stays stable across renders when the
  // underlying category data is unchanged. Consumers (e.g. IngredientRow) keep
  // this array in useCallback/memo deps, so an unstable reference would defeat
  // their React.memo and re-render every ingredient row on each keystroke.
  const options = useMemo<IngredientCategoryOption[]>(
    () => categories.map((c) => ({ value: c.value, label: c.label })),
    [categories]
  );

  return {
    options,
    categories,
    isLoading,
    error,
  };
}

/**
 * Fetch a single ingredient category by ID.
 */
export function useIngredientCategory(categoryId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: ingredientCategoryQueryKeys.detail(categoryId!),
    queryFn: async () => {
      const token = await getToken();
      return ingredientCategoryApi.get(categoryId!, token);
    },
    enabled: categoryId !== null,
    staleTime: 60000,
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Create a new custom ingredient category.
 */
export function useCreateIngredientCategory() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't add the category" },
    mutationFn: async (data: UserIngredientCategoryCreateDTO) => {
      const token = await getToken();
      return ingredientCategoryApi.create(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.lists(),
      });
    },
  });
}

/**
 * Update an ingredient category.
 */
export function useUpdateIngredientCategory() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't update the category" },
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: UserIngredientCategoryUpdateDTO;
    }) => {
      const token = await getToken();
      return ingredientCategoryApi.update(id, data, token);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.detail(id),
      });
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.lists(),
      });
    },
  });
}

/**
 * Delete a custom ingredient category.
 */
export function useDeleteIngredientCategory() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't delete the category" },
    mutationFn: async (id: number) => {
      const token = await getToken();
      return ingredientCategoryApi.delete(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.all,
      });
    },
  });
}

/**
 * Reorder ingredient categories.
 * Includes optimistic update for smooth UX.
 */
export function useReorderIngredientCategories() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't save the new order" },
    mutationFn: async (data: UserIngredientCategoryReorderDTO) => {
      const token = await getToken();
      return ingredientCategoryApi.reorder(data, token);
    },
    onMutate: async (data) => {
      await queryClient.cancelQueries({
        queryKey: ingredientCategoryQueryKeys.lists(),
      });

      const previous = queryClient.getQueryData<UserIngredientCategoryDTO[]>(
        ingredientCategoryQueryKeys.list(true)
      );

      if (previous) {
        const reordered = data.ordered_ids
          .map((id, index) => {
            const cat = previous.find((c) => c.id === id);
            return cat ? { ...cat, position: index } : null;
          })
          .filter(Boolean) as UserIngredientCategoryDTO[];

        queryClient.setQueryData(
          ingredientCategoryQueryKeys.list(true),
          reordered
        );
        queryClient.setQueryData(
          ingredientCategoryQueryKeys.list(false),
          reordered.filter((c) => c.is_enabled)
        );
      }

      return { previous };
    },
    onError: (_, __, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ingredientCategoryQueryKeys.list(true),
          context.previous
        );
        queryClient.setQueryData(
          ingredientCategoryQueryKeys.list(false),
          context.previous.filter((c) => c.is_enabled)
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.lists(),
      });
    },
  });
}

/**
 * Bulk update multiple ingredient categories.
 */
export function useBulkUpdateIngredientCategories() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't update categories" },
    mutationFn: async (data: UserIngredientCategoryBulkUpdateDTO) => {
      const token = await getToken();
      return ingredientCategoryApi.bulkUpdate(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.all,
      });
    },
  });
}

/**
 * Reset ingredient categories to defaults.
 */
export function useResetIngredientCategories() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't reset categories" },
    mutationFn: async () => {
      const token = await getToken();
      return ingredientCategoryApi.reset(token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientCategoryQueryKeys.all,
      });
    },
  });
}
