"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { billingApi } from "@/lib/api";
import { currentUserQueryKeys } from "./queryKeys";

/**
 * Fetch the current month's AI usage counters and tier caps.
 * Backs the usage meter in Settings → Plan & Billing.
 */
export function useMyUsage(enabled: boolean = true) {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  return useQuery({
    queryKey: currentUserQueryKeys.usage(),
    queryFn: async () => {
      const token = await getToken();
      return billingApi.getMyUsage(token);
    },
    enabled: enabled && isLoaded && !!isSignedIn,
    staleTime: 30000,
  });
}

/**
 * Start a Stripe Checkout session for the Pro plan and redirect to it.
 * The button stays in its loading state until the browser navigates away.
 */
export function useStartCheckout() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      const { checkout_url } = await billingApi.createCheckoutSession(token);
      window.location.assign(checkout_url);
    },
  });
}

/**
 * Open the Stripe billing portal (manage/cancel subscription) via redirect.
 */
export function useOpenBillingPortal() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      const { portal_url } = await billingApi.createPortalSession(token);
      window.location.assign(portal_url);
    },
  });
}
