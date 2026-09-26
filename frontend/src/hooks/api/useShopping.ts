"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { shoppingApi } from "@/lib/api";
import type {
  ShoppingListResponseDTO,
  ManualItemCreateDTO,
} from "@/types/shopping";

// ============================================================================
// QUERY KEYS
// ============================================================================

export const shoppingQueryKeys = {
  all: ["shopping"] as const,
  list: () => [...shoppingQueryKeys.all, "list"] as const,
  breakdown: (recipeIds: number[]) =>
    [...shoppingQueryKeys.all, "breakdown", recipeIds.sort().join(",")] as const,
};

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch the shopping list.
 * Shopping list is automatically synced when planner changes occur.
 */
export function useShoppingList() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  return useQuery({
    queryKey: shoppingQueryKeys.list(),
    queryFn: async () => {
      const token = await getToken();
      return shoppingApi.getList(undefined, token);
    },
    staleTime: 0, // Always fresh - shopping list changes frequently
    enabled: isLoaded && isSignedIn, // Only fetch when auth is ready
  });
}

/**
 * Hook to fetch ingredient breakdown for tooltips.
 * Only fetches if recipeIds are provided.
 */
export function useIngredientBreakdown(recipeIds: number[]) {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  return useQuery({
    queryKey: shoppingQueryKeys.breakdown(recipeIds),
    queryFn: async () => {
      const token = await getToken();
      return shoppingApi.getBreakdown(recipeIds, token);
    },
    enabled: isLoaded && isSignedIn && recipeIds.length > 0,
    staleTime: 30000, // Cache breakdown for 30 seconds (less volatile)
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Toggle item's "have" status with optimistic updates.
 */
function useShoppingField(field: "have" | "flagged") {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const patch = (id: number, value: boolean) => queryClient.setQueryData<ShoppingListResponseDTO>(shoppingQueryKeys.list(), old => {
    if (!old) return old;
    const items = old.items.map(item => item.id === id ? { ...item, [field]: value } : item);
    return { ...old, items, checked_items: items.filter(item => item.have).length };
  });
  return useMutation({
    mutationKey: ["shopping", "write"],
    mutationFn: async ({ id, value }: { id: number; value: boolean }) => shoppingApi.updateItem(id, { [field]: value }, await getToken()),
    onMutate: async ({ id, value }) => {
      await queryClient.cancelQueries({ queryKey: shoppingQueryKeys.list() });
      const previous = queryClient.getQueryData<ShoppingListResponseDTO>(shoppingQueryKeys.list())?.items.find(item => item.id === id)?.[field];
      patch(id, value);
      return { previous };
    },
    onSuccess: (item, { id }) => patch(id, item[field]),
    onError: (_error, { id }, context) => { if (context?.previous !== undefined) patch(id, context.previous); },
    onSettled: () => {
      if (queryClient.isMutating({ mutationKey: ["shopping", "write"] }) === 1) {
        void queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
        window.dispatchEvent(new Event("shopping-list-updated"));
      }
    },
  });
}
export function useToggleItem() { return useShoppingField("have"); }
export function useToggleFlagged() { return useShoppingField("flagged"); }

/**
 * Add a manual item.
 */
export function useAddManualItem() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ManualItemCreateDTO) => {
      const token = await getToken();
      return shoppingApi.addItem(data, token);
    },

    onSuccess: (newItem) => {
      // Add the new item to the cache
      const previousData = queryClient.getQueryData<ShoppingListResponseDTO>(
        shoppingQueryKeys.list()
      );

      if (previousData) {
        queryClient.setQueryData<ShoppingListResponseDTO>(
          shoppingQueryKeys.list(),
          {
            ...previousData,
            items: [...previousData.items, newItem],
            total_items: previousData.total_items + 1,
            manual_items: previousData.manual_items + 1,
          }
        );
      }

      window.dispatchEvent(new Event("shopping-list-updated"));
    },
  });
}

/**
 * Delete a shopping item with optimistic updates.
 */
export function useDeleteItem() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => shoppingApi.deleteItem(id, await getToken()),
    onSettled: () => { void queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() }); },
  });
}

/**
 * Clear manual items.
 */
export function useClearManualItems() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return shoppingApi.clearManual(token);
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      window.dispatchEvent(new Event("shopping-list-updated"));
    },
  });
}

/**
 * Clear completed items.
 */
export function useClearCompletedItems() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return shoppingApi.clearCompleted(token);
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      window.dispatchEvent(new Event("shopping-list-updated"));
    },
  });
}

/**
 * Generate shopping list from planner.
 * @deprecated Shopping list is now automatically synced when planner changes.
 * This hook is kept for backwards compatibility.
 */
export function useGenerateShoppingList() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return shoppingApi.generateFromPlanner(token);
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      window.dispatchEvent(new Event("shopping-list-updated"));
    },
  });
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Manually refresh the shopping list.
 */
export function useRefreshShoppingList() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
  };
}
