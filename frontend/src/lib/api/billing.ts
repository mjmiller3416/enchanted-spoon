import type {
  CheckoutSessionResponse,
  CurrentUserUsage,
  PortalSessionResponse,
} from "@/types/billing";
import { fetchApi } from "./base";

export const billingApi = {
  /** Create a Stripe Checkout session for the Pro plan; redirect to the returned URL. */
  createCheckoutSession: (token?: string | null): Promise<CheckoutSessionResponse> =>
    fetchApi<CheckoutSessionResponse>(
      "/api/billing/checkout-session",
      { method: "POST" },
      token,
    ),

  /** Create a Stripe billing-portal session; redirect to the returned URL. */
  createPortalSession: (token?: string | null): Promise<PortalSessionResponse> =>
    fetchApi<PortalSessionResponse>(
      "/api/billing/portal-session",
      { method: "POST" },
      token,
    ),

  /** Current month's AI usage counters and tier caps for the signed-in user. */
  getMyUsage: (token?: string | null): Promise<CurrentUserUsage> =>
    fetchApi<CurrentUserUsage>("/api/users/me/usage", undefined, token),
};
