"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { plannerApi } from "@/lib/api";
import { plannerQueryKeys, shoppingQueryKeys, dashboardQueryKeys } from "./queryKeys";
import { dispatchPlannerUpdate } from "./events";
import type {
  MealSelectionCreateDTO,
  MealSelectionUpdateDTO,
} from "@/types/meal";
import type {
  PlannerEntryResponseDTO,
} from "@/types/planner";
import type {
  ShoppingMode,
} from "@/types/shopping";

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch all planner entries with hydrated meal data.
 * Automatically refetches when cache is invalidated.
 */
export function usePlannerEntries() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: plannerQueryKeys.entries(),
    queryFn: async () => {
      const token = await getToken();
      return plannerApi.getEntries(token);
    },
    staleTime: 0, // Always fresh since planner changes frequently
  });
}

/**
 * Fetch a single meal by ID with full recipe data.
 * Used for SelectedMealCard and edit dialogs.
 */
export function useMeal(mealId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: plannerQueryKeys.meal(mealId!),
    queryFn: async () => {
      const token = await getToken();
      return plannerApi.getMeal(mealId!, token);
    },
    enabled: mealId !== null,
    staleTime: 30000, // 30 seconds - meal data changes less frequently
  });
}

/**
 * Fetch all meals, optionally filtered by saved status.
 */
export function useMeals(filters?: { saved?: boolean }) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: filters?.saved ? plannerQueryKeys.savedMeals() : plannerQueryKeys.meals(),
    queryFn: async () => {
      const token = await getToken();
      return plannerApi.getMeals(filters, token);
    },
    staleTime: 30000,
  });
}

/**
 * Fetch saved meals specifically.
 * Convenience wrapper around useMeals({ saved: true }).
 */
export function useSavedMeals() {
  return useMeals({ saved: true });
}

/**
 * Fetch the planner summary (entry counts + capacity).
 * Mutations don't invalidate this cache, so counts can lag behind the
 * entries list — prefer deriving live counts from usePlannerEntries and
 * reading only the server-owned capacity fields here.
 */
export function usePlannerSummary() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: plannerQueryKeys.summary(),
    queryFn: async () => {
      const token = await getToken();
      return plannerApi.getSummary(token);
    },
    staleTime: 60000, // 1 minute - max_capacity is effectively static
  });
}

/**
 * Fetch cooking streak data.
 * Includes current streak, longest streak, and week activity.
 */
export function useCookingStreak() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: plannerQueryKeys.streak(),
    queryFn: async () => {
      const token = await getToken();
      return plannerApi.getStreak(token);
    },
    staleTime: 60000, // 1 minute - streak changes only when meals are completed
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Create a new meal.
 * Invalidates saved meals list on success.
 */
export function useCreateMeal() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MealSelectionCreateDTO) => {
      const token = await getToken();
      return plannerApi.createMeal(data, token);
    },
    onSuccess: () => {
      // Invalidate meals lists as new meal may appear there
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.meals() });
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.savedMeals() });
    },
  });
}

/**
 * Update an existing meal.
 * Invalidates meal detail and entries cache.
 */
export function useUpdateMeal() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ mealId, data }: { mealId: number; data: MealSelectionUpdateDTO }) => {
      const token = await getToken();
      return plannerApi.updateMeal(mealId, data, token);
    },
    onSuccess: (updatedMeal) => {
      // Update the specific meal in cache
      queryClient.setQueryData(
        plannerQueryKeys.meal(updatedMeal.id),
        updatedMeal
      );
      // Invalidate entries as meal name/recipes may have changed
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.entries() });
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.savedMeals() });
      // Invalidate shopping list as ingredients may have changed
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Add a meal to the planner (creates a PlannerEntry).
 * With optimistic update for instant UI feedback.
 */
export function useAddToPlanner() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (mealId: number) => {
      const token = await getToken();
      return plannerApi.addToPlanner(mealId, token);
    },
    onSuccess: (newEntry) => {
      // Add entry to cache
      queryClient.setQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries(),
        (old) => (old ? [...old, newEntry] : [newEntry])
      );
      // Invalidate dashboard stats
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stats() });
      // Invalidate shopping list as it may need regeneration
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Remove a planner entry by entry ID.
 * With optimistic update for instant UI feedback.
 */
export function useRemoveEntry() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (entryId: number) => {
      const token = await getToken();
      return plannerApi.removeEntry(entryId, token);
    },
    onMutate: async (entryId) => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Capture the meal_id before removing (needed for cache cleanup)
      const entryToRemove = previousEntries?.find((e) => e.id === entryId);
      const removedMealId = entryToRemove?.meal_id ?? null;

      // Optimistically remove the entry
      if (previousEntries) {
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          previousEntries.filter((e) => e.id !== entryId)
        );
      }

      return { previousEntries, removedMealId };
    },
    onError: (_err, _entryId, context) => {
      // Rollback on error
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSettled: (_data, _error, _entryId, context) => {
      // Remove the meal from cache to prevent stale data (ghost selection bug fix)
      if (context?.removedMealId) {
        queryClient.removeQueries({
          queryKey: plannerQueryKeys.meal(context.removedMealId),
        });
      }

      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stats() });
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Mark a planner entry as complete (records recipe history).
 * With optimistic update for instant UI feedback.
 */
export function useMarkComplete() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (entryId: number) => {
      const token = await getToken();
      return plannerApi.markComplete(entryId, token);
    },
    onMutate: async (entryId) => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Optimistically mark as complete
      if (previousEntries) {
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          previousEntries.map((e) =>
            e.id === entryId
              ? { ...e, is_completed: true, completed_at: new Date().toISOString() }
              : e
          )
        );
      }

      return { previousEntries };
    },
    onError: (_err, _entryId, context) => {
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSuccess: (updatedEntry) => {
      // Update with server response to get exact completed_at
      queryClient.setQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries(),
        (old) =>
          old?.map((e) =>
            e.id === updatedEntry.id ? updatedEntry : e
          )
      );
      // Invalidate streak as completing a meal affects it
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.streak() });
    },
    onSettled: () => {
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Mark a planner entry as incomplete.
 * With optimistic update for instant UI feedback.
 */
export function useMarkIncomplete() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (entryId: number) => {
      const token = await getToken();
      return plannerApi.markIncomplete(entryId, token);
    },
    onMutate: async (entryId) => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Optimistically mark as incomplete
      if (previousEntries) {
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          previousEntries.map((e) =>
            e.id === entryId ? { ...e, is_completed: false, completed_at: null } : e
          )
        );
      }

      return { previousEntries };
    },
    onError: (_err, _entryId, context) => {
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSuccess: (updatedEntry) => {
      queryClient.setQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries(),
        (old) =>
          old?.map((e) =>
            e.id === updatedEntry.id ? updatedEntry : e
          )
      );
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.streak() });
    },
    onSettled: () => {
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Toggle a meal's saved status.
 * With optimistic update for instant UI feedback.
 */
export function useToggleSaveMeal() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (mealId: number) => {
      const token = await getToken();
      return plannerApi.toggleSave(mealId, token);
    },
    onMutate: async (mealId) => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Optimistically toggle saved status on entries
      if (previousEntries) {
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          previousEntries.map((e) =>
            e.meal_id === mealId
              ? { ...e, meal_is_saved: !e.meal_is_saved }
              : e
          )
        );
      }

      return { previousEntries };
    },
    onError: (_err, _mealId, context) => {
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSuccess: () => {
      // Invalidate saved meals list
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.savedMeals() });
    },
  });
}

/**
 * Cycle the shopping mode of a planner entry: all -> produce_only -> none -> all
 * With optimistic update for instant UI feedback.
 */
export function useCycleShoppingMode() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (entryId: number) => {
      const token = await getToken();
      return plannerApi.cycleShoppingMode(entryId, token);
    },
    onMutate: async (entryId) => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Calculate next mode optimistically
      const modes: ShoppingMode[] = ["all", "produce_only", "none"];
      if (previousEntries) {
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          previousEntries.map((e) => {
            if (e.id !== entryId) return e;
            const currentMode = e.shopping_mode ?? "all";
            const currentIndex = modes.indexOf(currentMode);
            const nextMode = modes[(currentIndex + 1) % modes.length];
            return { ...e, shopping_mode: nextMode };
          })
        );
      }

      return { previousEntries };
    },
    onError: (_err, _entryId, context) => {
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSettled: () => {
      // Shopping list needs regeneration after mode change
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Reorder planner entries by providing entry IDs in desired order.
 * With optimistic update for smooth drag-and-drop experience.
 */
export function useReorderEntries() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (entryIds: number[]) => {
      const token = await getToken();
      return plannerApi.reorderEntries(entryIds, token);
    },
    onMutate: async (entryIds) => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Optimistically reorder entries
      if (previousEntries) {
        const entryMap = new Map(previousEntries.map((e) => [e.id, e]));
        const reorderedActive = entryIds
          .map((id) => entryMap.get(id))
          .filter((e): e is PlannerEntryResponseDTO => e !== undefined);
        // Keep completed entries at the end (they're not in entryIds)
        const completedEntries = previousEntries.filter(
          (e) => e.is_completed && !entryIds.includes(e.id)
        );
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          [...reorderedActive, ...completedEntries]
        );
      }

      return { previousEntries };
    },
    onError: (_err, _entryIds, context) => {
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSettled: () => {
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Clear all completed planner entries.
 * With optimistic update for instant UI feedback.
 */
export function useClearCompleted() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return plannerApi.clearCompleted(token);
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: plannerQueryKeys.entries() });

      const previousEntries = queryClient.getQueryData<PlannerEntryResponseDTO[]>(
        plannerQueryKeys.entries()
      );

      // Optimistically remove completed entries
      if (previousEntries) {
        queryClient.setQueryData<PlannerEntryResponseDTO[]>(
          plannerQueryKeys.entries(),
          previousEntries.filter((e) => !e.is_completed)
        );
      }

      return { previousEntries };
    },
    onError: (_err, _void, context) => {
      if (context?.previousEntries) {
        queryClient.setQueryData(plannerQueryKeys.entries(), context.previousEntries);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stats() });
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.streak() });
      dispatchPlannerUpdate();
    },
  });
}

/**
 * Add a recipe as a side dish to a meal.
 * Invalidates the specific meal and entries cache.
 */
export function useAddSideToMeal() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ mealId, recipeId }: { mealId: number; recipeId: number }) => {
      const token = await getToken();
      return plannerApi.addSideToMeal(mealId, recipeId, token);
    },
    onSuccess: (updatedMeal) => {
      // Update the specific meal in cache
      queryClient.setQueryData(
        plannerQueryKeys.meal(updatedMeal.id),
        updatedMeal
      );
      // Invalidate entries as side recipes may show in preview
      queryClient.invalidateQueries({ queryKey: plannerQueryKeys.entries() });
      // Invalidate shopping list as new side dish ingredients need to be added
      queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
      dispatchPlannerUpdate();
    },
  });
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Manually refresh planner entries.
 * Useful for event-based refresh patterns.
 */
export function useRefreshPlannerEntries() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: plannerQueryKeys.entries() });
  };
}

/**
 * Manually refresh the cooking streak.
 */
export function useRefreshCookingStreak() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: plannerQueryKeys.streak() });
  };
}
