"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { adminApi } from "@/lib/api";
import { adminQueryKeys, currentUserQueryKeys } from "./queryKeys";
import type {
  AdminGrantProRequest,
  AdminToggleAdminRequest,
  AdminQueryResponse,
} from "@/types/admin";

// ============================================================================
// CURRENT USER HOOK
// ============================================================================

/**
 * Fetch the current user's profile including admin status.
 * Used to conditionally show admin sections in settings.
 */
export function useCurrentUser() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  const query = useQuery({
    queryKey: currentUserQueryKeys.all,
    queryFn: async () => {
      const token = await getToken();
      return adminApi.getCurrentUser(token);
    },
    enabled: isLoaded && !!isSignedIn,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    ...query,
    isAdmin: query.data?.is_admin ?? false,
  };
}

// ============================================================================
// ADMIN USER HOOKS
// ============================================================================

/**
 * Fetch paginated list of all users (admin only).
 */
export function useAdminUsers(skip: number = 0, limit: number = 50) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: [...adminQueryKeys.users(), { skip, limit }],
    queryFn: async () => {
      const token = await getToken();
      return adminApi.listUsers({ skip, limit }, token);
    },
    staleTime: 30000,
  });
}

/**
 * Fetch AI + import/create usage per user for a given month (admin only).
 * @param month Optional YYYY-MM string; defaults to the current UTC month server-side.
 */
export function useAdminUsage(month?: string) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: adminQueryKeys.usage(month),
    queryFn: async () => {
      const token = await getToken();
      return adminApi.getUsage(month, token);
    },
    staleTime: 30000,
  });
}

/**
 * Grant pro access to a user.
 */
export function useGrantPro() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      userId,
      data,
    }: {
      userId: number;
      data: AdminGrantProRequest;
    }) => {
      const token = await getToken();
      return adminApi.grantPro(userId, data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.users() });
    },
  });
}

/**
 * Revoke granted pro access from a user.
 */
export function useRevokePro() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number) => {
      const token = await getToken();
      return adminApi.revokePro(userId, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.users() });
    },
  });
}

/**
 * Toggle admin flag on a user.
 */
export function useToggleAdmin() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      userId,
      data,
    }: {
      userId: number;
      data: AdminToggleAdminRequest;
    }) => {
      const token = await getToken();
      return adminApi.toggleAdmin(userId, data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.users() });
    },
  });
}

/**
 * Delete a user and all their data.
 */
export function useDeleteUser() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number) => {
      const token = await getToken();
      return adminApi.deleteUser(userId, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.users() });
    },
  });
}

// ============================================================================
// ADMIN DATABASE QUERY HOOKS
// ============================================================================

/**
 * Execute a read-only SQL query against the database.
 */
export function useExecuteQuery() {
  const { getToken } = useAuth();

  return useMutation<AdminQueryResponse, Error, string>({
    mutationFn: async (query: string) => {
      const token = await getToken();
      return adminApi.executeQuery({ query }, token);
    },
  });
}

