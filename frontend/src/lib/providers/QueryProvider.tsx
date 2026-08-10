"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { maybeHandleAiGateError } from "@/lib/paywall";

export function QueryProvider({ children }: { children: ReactNode }) {
  // Create QueryClient inside useState to avoid recreating on every render
  const [queryClient] = useState(
    () =>
      new QueryClient({
        // One interception layer for AI access gates (#166): any mutation that
        // fails with a pro-required 403 or usage-limit 429 opens the paywall
        // dialog. Call-site onError handlers still run; they use
        // classifyAiGateError/maybeHandleAiGateError to skip generic toasts.
        mutationCache: new MutationCache({
          onError: (error) => {
            maybeHandleAiGateError(error);
          },
        }),
        defaultOptions: {
          queries: {
            // Keep data fresh - no aggressive caching per user preference
            staleTime: 0,
            // Refetch when window regains focus for freshness
            refetchOnWindowFocus: true,
            // Retry failed requests once
            retry: 1,
            // Don't refetch on reconnect (user can refresh manually)
            refetchOnReconnect: false,
          },
          mutations: {
            // Retry mutations once on failure
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
