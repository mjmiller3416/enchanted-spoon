/**
 * Authenticated API Client
 *
 * Provides hooks and functions for making authenticated API requests using Clerk tokens.
 * This wraps the existing api.ts functions with automatic token injection.
 */

"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import { ApiError } from "@/lib/api/base";

// API base URL from environment variable or default to localhost
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://192.168.1.213:8000";

/**
 * Core authenticated fetch function for client components
 * @param endpoint - API endpoint (e.g., "/api/recipes")
 * @param options - Fetch options (method, body, etc.)
 * @param token - Bearer token from Clerk
 * @returns Parsed JSON response
 */
export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit,
  token?: string | null
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  // Add Authorization header if token is provided
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - Clerk proxy will redirect
  if (response.status === 401) {
    throw new ApiError("Unauthorized - Please sign in", 401);
  }

  if (!response.ok) {
    let errorMessage = `API Error: ${response.status}`;
    let details: Record<string, unknown> | undefined;

    try {
      const errorData = await response.json();
      // `detail` may be a structured object (e.g. usage_limit_exceeded 429s) —
      // never let an object become the Error message.
      const detail = errorData.detail;
      errorMessage =
        (typeof detail === "string" ? detail : detail?.message) ||
        errorData.message ||
        errorMessage;
      details = errorData;
    } catch {
      // Ignore JSON parse errors
    }

    throw new ApiError(errorMessage, response.status, details);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  return JSON.parse(text);
}

/**
 * Server-side authenticated fetch function for server components
 * @param endpoint - API endpoint (e.g., "/api/recipes")
 * @param token - Bearer token from auth() in server components
 * @param options - Fetch options (method, body, etc.)
 * @returns Parsed JSON response
 */
export async function apiServerFetch<T>(
  endpoint: string,
  token: string | null,
  options?: RequestInit
): Promise<T> {
  return apiFetch<T>(endpoint, options, token);
}

/**
 * Hook that provides an authenticated fetch function for client components.
 * Automatically retrieves and attaches the Clerk auth token to requests.
 *
 * @example
 * ```tsx
 * const { apiFetch } = useApiClient();
 *
 * // Make an authenticated request
 * const recipes = await apiFetch<RecipeResponseDTO[]>("/api/recipes");
 *
 * // With options
 * const newRecipe = await apiFetch<RecipeResponseDTO>("/api/recipes", {
 *   method: "POST",
 *   body: JSON.stringify(data),
 * });
 * ```
 */
export function useApiClient() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  /**
   * Authenticated fetch function
   * Automatically includes the Clerk auth token
   */
  const authenticatedFetch = useCallback(
    async <T>(endpoint: string, options?: RequestInit): Promise<T> => {
      // Get fresh token for each request
      const token = await getToken();
      return apiFetch<T>(endpoint, options, token);
    },
    [getToken]
  );

  /**
   * Get the current auth token (useful for custom fetch scenarios)
   */
  const getAuthToken = useCallback(async () => {
    return await getToken();
  }, [getToken]);

  return useMemo(
    () => ({
      apiFetch: authenticatedFetch,
      getToken: getAuthToken,
      isLoaded,
      isSignedIn,
    }),
    [authenticatedFetch, getAuthToken, isLoaded, isSignedIn]
  );
}

// ============================================================================
// Query string builder (exported for use in hooks)
// ============================================================================

export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      searchParams.append(key, String(value));
    }
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}
