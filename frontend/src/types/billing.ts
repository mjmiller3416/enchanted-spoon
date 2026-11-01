// Billing + usage-meter types matching backend DTOs

/** Per-field monthly caps. `null` means unlimited (admins, uncapped fields). */
export interface UsageLimits {
  ai_images_generated: number | null;
  ai_suggestions_requested: number | null;
  ai_assistant_messages: number | null;
  recipes_imported: number | null;
}

/** Response from GET /api/users/me/usage — the settings usage meter. */
export interface CurrentUserUsage {
  month: string;
  ai_images_generated: number;
  ai_suggestions_requested: number;
  ai_assistant_messages: number;
  recipes_imported: number;
  limits: UsageLimits;
  usage_tier: string;
  resets: "monthly" | "trial" | "none";
  /** True when the numbers are the household owner's shared pool. */
  shared_with_household?: boolean;
}

export interface FounderSpot {
  code: string;
  plan: string;
  spots_remaining: number | null;
  spots_total: number | null;
}

export interface FounderOffer {
  ends_at: string;
  monthly: FounderSpot;
  annual: FounderSpot;
}

export type CheckoutPlan = "monthly" | "annual";

export interface CheckoutSessionResponse {
  checkout_url: string;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export interface StoreSyncResponse {
  result: string;
}
