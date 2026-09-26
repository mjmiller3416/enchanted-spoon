// Core API infrastructure: fetch wrapper, error handling, query string builder

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Default request timeout. AI endpoints (image/recipe generation, chat) can
// legitimately run long, so those call sites pass a larger AI_TIMEOUT_MS.
export const DEFAULT_TIMEOUT_MS = 30_000;
export const AI_TIMEOUT_MS = 90_000;

export class ApiError extends Error {
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/**
 * Build an ApiError from a failed response without ever throwing a parse
 * error of its own. Proxies (Railway 502/504, 413) answer with HTML, and
 * FastAPI's `detail` can be a string, a structured object (e.g.
 * usage_limit_exceeded 429s carry {error, field, current, limit, message}),
 * or a 422 validation array — none of which may leak into the UI as
 * "Unexpected token '<'" or "[object Object]".
 */
export async function toApiError(response: Response, fallback: string): Promise<ApiError> {
  let errorData: Record<string, unknown> | undefined;
  try {
    errorData = await response.json();
  } catch {
    // Non-JSON body (HTML error page, empty response)
  }

  const detail = errorData?.detail;
  let message: string | undefined;
  if (typeof detail === "string") {
    message = detail;
  } else if (Array.isArray(detail)) {
    message = detail
      .map((d) => (typeof d?.msg === "string" ? d.msg.replace(/^Value error, /, "") : null))
      .filter(Boolean)
      .join("; ");
  } else if (detail && typeof detail === "object") {
    const nested = (detail as { message?: unknown }).message;
    if (typeof nested === "string") message = nested;
  }
  if (!message && typeof errorData?.message === "string") {
    message = errorData.message;
  }
  if (!message && response.status === 413) {
    message = "That file is too large to upload.";
  }
  if (!message && response.status >= 500) {
    message = `${fallback}. The server had a problem — please try again in a moment.`;
  }

  return new ApiError(message || fallback, response.status, errorData);
}

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
  token?: string | null,
  timeoutMs: number = DEFAULT_TIMEOUT_MS
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

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError(`Request timed out after ${timeoutMs}ms`, 408);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw await toApiError(response, `API Error: ${response.status}`);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  return JSON.parse(text);
}

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
