"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { categoryApi } from "@/lib/api";
import type {
  UserCategoryDTO,
  UserCategoryCreateDTO,
  UserCategoryUpdateDTO,
  UserCategoryReorderDTO,
  UserCategoryBulkUpdateDTO,
  CategoryOption,
} from "@/types/category";

// ============================================================================
// QUERY KEYS
// ============================================================================

export const categoryQueryKeys = {
  all: ["categories"] as const,
  lists: () => [...categoryQueryKeys.all, "list"] as const,
  list: (includeDisabled?: boolean) =>
    [...categoryQueryKeys.lists(), { includeDisabled }] as const,
  details: () => [...categoryQueryKeys.all, "detail"] as const,
  detail: (id: number) => [...categoryQueryKeys.details(), id] as const,
};

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch all categories for the current user.
 * Returns categories ordered by position.
 * On first access, built-in categories are automatically seeded.
 *
 * @param includeDisabled - Include disabled categories (default: false)
 */
export function useCategories(includeDisabled = false) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: categoryQueryKeys.list(includeDisabled),
    queryFn: async () => {
      const token = await getToken();
      return categoryApi.list(token, includeDisabled);
    },
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Convenience hook: Get categories formatted as filter options.
 *
 * Returns:
 * - filterOptions: Includes "All" at the start (for filter UIs)
 * - formOptions: Excludes "All" (for form dropdowns)
 * - categories: Raw category data
 * - isLoading: Loading state
 * - error: Error state
 *
 * This hook replaces the static RECIPE_CATEGORIES constant.
 */
export function useCategoryOptions() {
  const { data: categories = [], isLoading, error } = useCategories(false);

  // Memoize so option references stay stable across renders when the
  // underlying category data is unchanged — an unstable reference can defeat
  // React.memo / useCallback deps in consuming form components.
  // Filter options include "All" at the start for filter UIs.
  const filterOptions = useMemo<CategoryOption[]>(
    () => [
      { value: "all", label: "All" },
      ...categories.map((c) => ({ value: c.value, label: c.label })),
    ],
    [categories]
  );

  // Form options exclude "All" for form dropdowns.
  const formOptions = useMemo<CategoryOption[]>(
    () => categories.map((c) => ({ value: c.value, label: c.label })),
    [categories]
  );

  return {
    filterOptions,
    formOptions,
    categories,
    isLoading,
    error,
  };
}

/**
 * Fetch a single category by ID.
 */
export function useCategory(categoryId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: categoryQueryKeys.detail(categoryId!),
    queryFn: async () => {
      const token = await getToken();
      return categoryApi.get(categoryId!, token);
    },
    enabled: categoryId !== null,
    staleTime: 60000, // 1 minute
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Create a new custom category.
 */
export function useCreateCategory() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't add the category" },
    mutationFn: async (data: UserCategoryCreateDTO) => {
      const token = await getToken();
      return categoryApi.create(data, token);
    },
    onSuccess: () => {
      // Invalidate category lists
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.lists() });
    },
  });
}

/**
 * Update a category.
 */
export function useUpdateCategory() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't update the category" },
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: UserCategoryUpdateDTO;
    }) => {
      const token = await getToken();
      return categoryApi.update(id, data, token);
    },
    onSuccess: (_, { id }) => {
      // Invalidate specific category and lists
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.lists() });
    },
  });
}

/**
 * Delete a custom category.
 */
export function useDeleteCategory() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't delete the category" },
    mutationFn: async (id: number) => {
      const token = await getToken();
      return categoryApi.delete(id, token);
    },
    onSuccess: () => {
      // Invalidate all category queries
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.all });
    },
  });
}

/**
 * Reorder categories.
 * Includes optimistic update for smooth UX.
 */
export function useReorderCategories() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't save the new order" },
    mutationFn: async (data: UserCategoryReorderDTO) => {
      const token = await getToken();
      return categoryApi.reorder(data, token);
    },
    onMutate: async (data) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: categoryQueryKeys.lists() });

      // Snapshot for rollback
      const previous = queryClient.getQueryData<UserCategoryDTO[]>(
        categoryQueryKeys.list(true)
      );

      // Optimistic update - reorder locally
      if (previous) {
        const reordered = data.ordered_ids
          .map((id, index) => {
            const cat = previous.find((c) => c.id === id);
            return cat ? { ...cat, position: index } : null;
          })
          .filter(Boolean) as UserCategoryDTO[];

        queryClient.setQueryData(categoryQueryKeys.list(true), reordered);
        queryClient.setQueryData(
          categoryQueryKeys.list(false),
          reordered.filter((c) => c.is_enabled)
        );
      }

      return { previous };
    },
    onError: (_, __, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(
          categoryQueryKeys.list(true),
          context.previous
        );
        queryClient.setQueryData(
          categoryQueryKeys.list(false),
          context.previous.filter((c) => c.is_enabled)
        );
      }
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.lists() });
    },
  });
}

/**
 * Bulk update multiple categories.
 */
export function useBulkUpdateCategories() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't update categories" },
    mutationFn: async (data: UserCategoryBulkUpdateDTO) => {
      const token = await getToken();
      return categoryApi.bulkUpdate(data, token);
    },
    onSuccess: () => {
      // Invalidate all category queries
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.all });
    },
  });
}

/**
 * Reset categories to defaults.
 */
export function useResetCategories() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't reset categories" },
    mutationFn: async () => {
      const token = await getToken();
      return categoryApi.reset(token);
    },
    onSuccess: () => {
      // Invalidate all category queries
      queryClient.invalidateQueries({ queryKey: categoryQueryKeys.all });
    },
  });
}
