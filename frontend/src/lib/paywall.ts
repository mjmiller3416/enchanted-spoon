// Single interception layer for AI access errors (#166).
//
// The backend gates AI features three ways:
//   {error: "trial_required"}            → start the 7-day trial
//   403 "Pro subscription required..."  → feature needs a Pro plan
//   429 {error: "usage_limit_exceeded"} → monthly tier cap hit (carries current/limit)
//
// Trial checkout is chosen by the error code `trial_required`, not by HTTP
// 403. The web paywall and the #209 native paywall must both do that. 403 is
// also returned for read-only accounts and for "Pro subscription required".
//
// Both are classified here and surfaced through one PaywallDialog (mounted in
// AppLayout), which subscribes via `subscribePaywall`. React Query mutations
// are intercepted globally in QueryProvider's MutationCache; non-React-Query
// call sites (e.g. the wizard's URL import) call `maybeHandleAiGateError`
// directly and skip their own generic error UI when it returns true.

import { ApiError } from "@/lib/api/base";

export type PaywallReason = "pro_required" | "limit_reached" | "trial_required";

export interface PaywallEvent {
  reason: PaywallReason;
  /** Human-readable feature name, e.g. "AI image generation". */
  featureLabel: string;
  current?: number;
  limit?: number;
}

type PaywallListener = (event: PaywallEvent) => void;

const listeners = new Set<PaywallListener>();

export function subscribePaywall(listener: PaywallListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function openPaywall(event: PaywallEvent): void {
  listeners.forEach((listener) => listener(event));
}

const FIELD_LABELS: Record<string, string> = {
  ai_images_generated: "AI photos",
  ai_suggestions_requested: "AI suggestions",
  ai_assistant_messages: "assistant messages",
  recipes_imported: "recipe imports",
};

/**
 * Classify an error as an AI access-gate error, or return null.
 */
function gateErrorCode(error: ApiError): string | null {
  const detail = error.details?.detail;
  if (!detail || typeof detail !== "object" || Array.isArray(detail)) return null;
  const code = (detail as { error?: unknown }).error;
  return typeof code === "string" ? code : null;
}

export function classifyAiGateError(error: unknown): PaywallEvent | null {
  if (!(error instanceof ApiError)) return null;

  // Error code first. A non-403 response with this code still opens trial checkout.
  if (gateErrorCode(error) === "trial_required") {
    return { reason: "trial_required", featureLabel: "AI features" };
  }

  if (error.status === 403) {
    const detail = error.details?.detail;
    if (gateErrorCode(error) === "read_only") {
      return { reason: "pro_required", featureLabel: "creating, planning, and AI" };
    }
    const message = typeof detail === "string" ? detail : error.message;
    if (typeof message === "string" && message.includes("Pro subscription required")) {
      return { reason: "pro_required", featureLabel: "this AI feature" };
    }
    return null;
  }

  if (error.status === 429) {
    const detail = error.details?.detail;
    if (
      detail &&
      typeof detail === "object" &&
      !Array.isArray(detail) &&
      (detail as Record<string, unknown>).error === "usage_limit_exceeded"
    ) {
      const d = detail as { field?: string; current?: number; limit?: number };
      return {
        reason: "limit_reached",
        featureLabel: FIELD_LABELS[d.field ?? ""] ?? "this AI feature",
        current: d.current,
        limit: d.limit,
      };
    }
    return null;
  }

  return null;
}

/**
 * If the error is an AI access-gate error, open the paywall dialog and
 * return true (callers should skip their own generic error UI).
 */
export function maybeHandleAiGateError(error: unknown): boolean {
  const event = classifyAiGateError(error);
  if (!event) return false;
  openPaywall(event);
  return true;
}

/** Chat bubble that matches the paywall the mutation cache already opened. */
export function aiGateChatReply(error: unknown): string {
  const event = classifyAiGateError(error);
  if (!event) return "Sorry, something went wrong. Please try again.";
  if (event.reason === "trial_required") return "Start your 7-day trial to use AI.";
  return "You've used this month's assistant allowance — see the upgrade options to keep chatting.";
}
