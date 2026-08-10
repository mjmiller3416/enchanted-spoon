/**
 * Server-side Authenticated API Client
 *
 * Provides functions for making authenticated API requests from server components
 * using Clerk's auth() function.
 */

import { auth } from "@clerk/nextjs/server";
import { ApiError } from "@/lib/api/base";

// API base URL from environment variable, defaulting to the local dev backend.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Server-side authenticated fetch function for server components.
 * Automatically retrieves the auth token from Clerk's auth() function.
 *
 * @param endpoint - API endpoint (e.g., "/api/recipes")
 * @param options - Fetch options (method, body, etc.)
 * @returns Parsed JSON response
 *
 * @example
 * ```tsx
 * // In a server component
 * import { apiServerFetch } from "@/lib/api-server";
 *
 * export default async function RecipesPage() {
 *   const recipes = await apiServerFetch<RecipeResponseDTO[]>("/api/recipes");
 *   return <RecipeList recipes={recipes} />;
 * }
 * ```
 */
export async function apiServerFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  // Get auth session and token from Clerk
  const { getToken } = await auth();
  const token = await getToken();

  const url = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  // Add Authorization header if token is available
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized
  if (response.status === 401) {
    throw new ApiError("Unauthorized - Please sign in", 401);
  }

  if (!response.ok) {
    let errorMessage = `API Error: ${response.status}`;
    let details: Record<string, unknown> | undefined;

    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
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
 * Server-side authenticated fetch with explicit token parameter.
 * Use this when you already have the token from auth().
 *
 * @param endpoint - API endpoint (e.g., "/api/recipes")
 * @param token - Bearer token from auth().getToken()
 * @param options - Fetch options (method, body, etc.)
 * @returns Parsed JSON response
 *
 * @example
 * ```tsx
 * // When you need to pass the token explicitly
 * import { auth } from "@clerk/nextjs/server";
 * import { apiServerFetchWithToken } from "@/lib/api-server";
 *
 * export default async function RecipesPage() {
 *   const { getToken } = await auth();
 *   const token = await getToken();
 *   const recipes = await apiServerFetchWithToken<RecipeResponseDTO[]>("/api/recipes", token);
 *   return <RecipeList recipes={recipes} />;
 * }
 * ```
 */
export async function apiServerFetchWithToken<T>(
  endpoint: string,
  token: string | null,
  options?: RequestInit
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

  // Handle 401 Unauthorized
  if (response.status === 401) {
    throw new ApiError("Unauthorized - Please sign in", 401);
  }

  if (!response.ok) {
    let errorMessage = `API Error: ${response.status}`;
    let details: Record<string, unknown> | undefined;

    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
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

// ============================================================================
// Query string builder (exported for use in server components)
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
