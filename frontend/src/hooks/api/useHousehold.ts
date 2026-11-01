"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { householdApi } from "@/lib/api";
import {
  currentUserQueryKeys,
  householdQueryKeys,
  plannerQueryKeys,
  recipeQueryKeys,
} from "./queryKeys";
import { shoppingQueryKeys } from "./useShopping";

function useRefreshSharedKitchen() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: householdQueryKeys.all });
    queryClient.invalidateQueries({ queryKey: plannerQueryKeys.all });
    queryClient.invalidateQueries({ queryKey: recipeQueryKeys.all });
    queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.all });
    queryClient.invalidateQueries({ queryKey: currentUserQueryKeys.all });
  };
}

export function useHousehold() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  return useQuery({
    queryKey: householdQueryKeys.state(),
    queryFn: async () => householdApi.get(await getToken()),
    enabled: isLoaded && !!isSignedIn,
  });
}

export function useCreateHousehold() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (name: string) => householdApi.create(name, await getToken()),
    onSuccess: refresh,
  });
}

export function useRenameHousehold() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (name: string) => householdApi.rename(name, await getToken()),
    onSuccess: refresh,
  });
}

export function useDissolveHousehold() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async () => householdApi.dissolve(await getToken()),
    onSuccess: refresh,
  });
}

export function useCreateHouseholdInvite() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (email: string | null) => householdApi.createInvite(email, await getToken()),
    onSuccess: refresh,
  });
}

export function useRevokeHouseholdInvite() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (inviteId: number) => householdApi.revokeInvite(inviteId, await getToken()),
    onSuccess: refresh,
  });
}

export function useJoinHousehold() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (code: string) => householdApi.join(code, await getToken()),
    onSuccess: refresh,
  });
}

export function useLeaveHousehold() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async () => householdApi.leave(await getToken()),
    onSuccess: refresh,
  });
}

export function useRemoveHouseholdMember() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (userId: number) => householdApi.removeMember(userId, await getToken()),
    onSuccess: refresh,
  });
}

export function useTransferHousehold() {
  const { getToken } = useAuth();
  const refresh = useRefreshSharedKitchen();
  return useMutation({
    mutationFn: async (userId: number) => householdApi.transfer(userId, await getToken()),
    onSuccess: refresh,
  });
}

export function useSetHouseholdRecipeShare() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ recipeId, shared }: { recipeId: number; shared: boolean }) => {
      const token = await getToken();
      if (shared) {
        await householdApi.shareRecipe(recipeId, token);
      } else {
        await householdApi.unshareRecipe(recipeId, token);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recipeQueryKeys.all });
    },
  });
}
