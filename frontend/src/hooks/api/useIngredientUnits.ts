"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { ingredientUnitApi } from "@/lib/api";
import type {
  UserIngredientUnitDTO,
  UserIngredientUnitCreateDTO,
  UserIngredientUnitUpdateDTO,
  UserIngredientUnitReorderDTO,
  UserIngredientUnitBulkUpdateDTO,
  IngredientUnitOption,
} from "@/types/ingredient-settings";

// ============================================================================
// QUERY KEYS
// ============================================================================

export const ingredientUnitQueryKeys = {
  all: ["ingredient-units"] as const,
  lists: () => [...ingredientUnitQueryKeys.all, "list"] as const,
  list: (includeDisabled?: boolean) =>
    [...ingredientUnitQueryKeys.lists(), { includeDisabled }] as const,
  details: () => [...ingredientUnitQueryKeys.all, "detail"] as const,
  detail: (id: number) =>
    [...ingredientUnitQueryKeys.details(), id] as const,
};

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch all ingredient units for the current user.
 * Returns units ordered by position.
 * On first access, built-in units are automatically seeded.
 */
export function useIngredientUnits(includeDisabled = false) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: ingredientUnitQueryKeys.list(includeDisabled),
    queryFn: async () => {
      const token = await getToken();
      return ingredientUnitApi.list(token, includeDisabled);
    },
    staleTime: 30000,
  });
}

/**
 * Convenience hook: Get ingredient units formatted as dropdown options.
 *
 * Returns:
 * - options: Units as { value, label, unit_type } for form dropdowns
 * - units: Raw unit data
 * - isLoading: Loading state
 * - error: Error state
 *
 * This hook replaces hardcoded unit lists in forms.
 */
export function useIngredientUnitOptions() {
  const { data: units = [], isLoading, error } = useIngredientUnits(false);

  const options: IngredientUnitOption[] = units.map((u) => ({
    value: u.value,
    label: u.label,
    unit_type: u.unit_type,
  }));

  return {
    options,
    units,
    isLoading,
    error,
  };
}

/**
 * Fetch a single ingredient unit by ID.
 */
export function useIngredientUnit(unitId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: ingredientUnitQueryKeys.detail(unitId!),
    queryFn: async () => {
      const token = await getToken();
      return ingredientUnitApi.get(unitId!, token);
    },
    enabled: unitId !== null,
    staleTime: 60000,
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Create a new custom ingredient unit.
 */
export function useCreateIngredientUnit() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't add the unit" },
    mutationFn: async (data: UserIngredientUnitCreateDTO) => {
      const token = await getToken();
      return ingredientUnitApi.create(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.lists(),
      });
    },
  });
}

/**
 * Update an ingredient unit.
 */
export function useUpdateIngredientUnit() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't update the unit" },
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: UserIngredientUnitUpdateDTO;
    }) => {
      const token = await getToken();
      return ingredientUnitApi.update(id, data, token);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.detail(id),
      });
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.lists(),
      });
    },
  });
}

/**
 * Delete a custom ingredient unit.
 */
export function useDeleteIngredientUnit() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't delete the unit" },
    mutationFn: async (id: number) => {
      const token = await getToken();
      return ingredientUnitApi.delete(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.all,
      });
    },
  });
}

/**
 * Reorder ingredient units.
 * Includes optimistic update for smooth UX.
 */
export function useReorderIngredientUnits() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't save the new order" },
    mutationFn: async (data: UserIngredientUnitReorderDTO) => {
      const token = await getToken();
      return ingredientUnitApi.reorder(data, token);
    },
    onMutate: async (data) => {
      await queryClient.cancelQueries({
        queryKey: ingredientUnitQueryKeys.lists(),
      });

      const previous = queryClient.getQueryData<UserIngredientUnitDTO[]>(
        ingredientUnitQueryKeys.list(true)
      );

      if (previous) {
        const reordered = data.ordered_ids
          .map((id, index) => {
            const unit = previous.find((u) => u.id === id);
            return unit ? { ...unit, position: index } : null;
          })
          .filter(Boolean) as UserIngredientUnitDTO[];

        queryClient.setQueryData(
          ingredientUnitQueryKeys.list(true),
          reordered
        );
        queryClient.setQueryData(
          ingredientUnitQueryKeys.list(false),
          reordered.filter((u) => u.is_enabled)
        );
      }

      return { previous };
    },
    onError: (_, __, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ingredientUnitQueryKeys.list(true),
          context.previous
        );
        queryClient.setQueryData(
          ingredientUnitQueryKeys.list(false),
          context.previous.filter((u) => u.is_enabled)
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.lists(),
      });
    },
  });
}

/**
 * Bulk update multiple ingredient units.
 */
export function useBulkUpdateIngredientUnits() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't update units" },
    mutationFn: async (data: UserIngredientUnitBulkUpdateDTO) => {
      const token = await getToken();
      return ingredientUnitApi.bulkUpdate(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.all,
      });
    },
  });
}

/**
 * Reset ingredient units to defaults.
 */
export function useResetIngredientUnits() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't reset units" },
    mutationFn: async () => {
      const token = await getToken();
      return ingredientUnitApi.reset(token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ingredientUnitQueryKeys.all,
      });
    },
  });
}
