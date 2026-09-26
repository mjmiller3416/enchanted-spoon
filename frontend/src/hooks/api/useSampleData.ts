"use client";

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { sampleDataApi } from "@/lib/api";
import { invalidateRecipeDependents } from "./invalidateRecipeDependents";
import { sampleDataQueryKeys } from "./queryKeys";

/** Starter content touches recipes, meals, the planner, and the shopping list */
function invalidateSampleData(client: QueryClient) {
  return Promise.all([
    invalidateRecipeDependents(client),
    client.invalidateQueries({ queryKey: sampleDataQueryKeys.all }),
  ]);
}

/**
 * Whether the account still has untouched onboarding starter content.
 * New accounts are seeded with it on first sign-in.
 */
export function useSampleDataStatus(enabled: boolean = true) {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  return useQuery({
    queryKey: sampleDataQueryKeys.status(),
    queryFn: async () => {
      const token = await getToken();
      return sampleDataApi.getStatus(token);
    },
    enabled: enabled && isLoaded && !!isSignedIn,
    staleTime: 60000,
  });
}

/** Add the starter pack (recipes, meals, planner entries, shopping list). */
export function useAddSampleData() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return sampleDataApi.add(token);
    },
    onSettled: () => invalidateSampleData(queryClient),
  });
}

/** Remove untouched sample recipes and meals; edited ones are kept. */
export function useRemoveSampleData() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return sampleDataApi.remove(token);
    },
    onSettled: () => invalidateSampleData(queryClient),
  });
}
