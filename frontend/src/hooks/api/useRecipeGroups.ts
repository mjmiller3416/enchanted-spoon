"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { recipeGroupApi } from "@/lib/api";
import { recipeQueryKeys } from "./queryKeys";
import type {
  RecipeGroupCreateDTO,
  RecipeGroupUpdateDTO,
  RecipeGroupAssignmentDTO,
} from "@/types/recipe";

// ============================================================================
// QUERY KEYS
// ============================================================================

export const recipeGroupQueryKeys = {
  all: ["recipeGroups"] as const,
  lists: () => [...recipeGroupQueryKeys.all, "list"] as const,
  list: () => [...recipeGroupQueryKeys.lists()] as const,
  details: () => [...recipeGroupQueryKeys.all, "detail"] as const,
  detail: (id: number) => [...recipeGroupQueryKeys.details(), id] as const,
  byRecipe: (recipeId: number) => [...recipeGroupQueryKeys.all, "byRecipe", recipeId] as const,
};

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch all recipe groups for the current user.
 * Returns groups ordered alphabetically by name with recipe counts.
 */
export function useRecipeGroups() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeGroupQueryKeys.list(),
    queryFn: async () => {
      const token = await getToken();
      return recipeGroupApi.list(token);
    },
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Fetch a single recipe group by ID.
 */
export function useRecipeGroup(groupId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeGroupQueryKeys.detail(groupId!),
    queryFn: async () => {
      const token = await getToken();
      return recipeGroupApi.get(groupId!, token);
    },
    enabled: groupId !== null,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Fetch all groups that contain a specific recipe.
 */
export function useRecipeGroupsForRecipe(recipeId: number | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: recipeGroupQueryKeys.byRecipe(recipeId!),
    queryFn: async () => {
      const token = await getToken();
      return recipeGroupApi.getGroupsForRecipe(recipeId!, token);
    },
    enabled: recipeId !== null,
    staleTime: 30000, // 30 seconds
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Create a new recipe group.
 */
export function useCreateRecipeGroup() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RecipeGroupCreateDTO) => {
      const token = await getToken();
      return recipeGroupApi.create(data, token);
    },
    onSuccess: () => {
      // Invalidate groups list
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.lists() });
    },
  });
}

/**
 * Update a recipe group's name.
 */
export function useUpdateRecipeGroup() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't rename the group" },
    mutationFn: async ({ id, data }: { id: number; data: RecipeGroupUpdateDTO }) => {
      const token = await getToken();
      return recipeGroupApi.update(id, data, token);
    },
    onSuccess: (_, { id }) => {
      // Invalidate specific group and list
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.lists() });
    },
  });
}

/**
 * Delete a recipe group.
 */
export function useDeleteRecipeGroup() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    meta: { errorMessage: "Couldn't delete the group" },
    mutationFn: async (id: number) => {
      const token = await getToken();
      return recipeGroupApi.delete(id, token);
    },
    onSuccess: () => {
      // Invalidate all group queries
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.all });
      // Also invalidate recipe queries since group assignments changed
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.all });
    },
  });
}

/**
 * Assign a recipe to specific groups (replaces existing assignments).
 */
export function useAssignRecipeToGroups() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      recipeId,
      data,
    }: {
      recipeId: number;
      data: RecipeGroupAssignmentDTO;
    }) => {
      const token = await getToken();
      return recipeGroupApi.assignRecipeToGroups(recipeId, data, token);
    },
    onSuccess: (_, { recipeId }) => {
      // Invalidate groups for this recipe
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.byRecipe(recipeId) });
      // Invalidate all groups list (recipe counts changed)
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.lists() });
    },
  });
}

/**
 * Add a recipe to a group.
 */
export function useAddRecipeToGroup() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ groupId, recipeId }: { groupId: number; recipeId: number }) => {
      const token = await getToken();
      return recipeGroupApi.addRecipeToGroup(groupId, recipeId, token);
    },
    onSuccess: (_, { groupId, recipeId }) => {
      // Invalidate specific group and recipe's groups
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.detail(groupId) });
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.byRecipe(recipeId) });
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.lists() });
    },
  });
}

/**
 * Remove a recipe from a group.
 */
export function useRemoveRecipeFromGroup() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ groupId, recipeId }: { groupId: number; recipeId: number }) => {
      const token = await getToken();
      return recipeGroupApi.removeRecipeFromGroup(groupId, recipeId, token);
    },
    onSuccess: (_, { groupId, recipeId }) => {
      // Invalidate specific group and recipe's groups
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.detail(groupId) });
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.byRecipe(recipeId) });
      queryClient.invalidateQueries({ queryKey: recipeGroupQueryKeys.lists() });
    },
  });
}
