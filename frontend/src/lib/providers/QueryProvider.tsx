"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { maybeHandleAiGateError } from "@/lib/paywall";
import { getErrorMessage } from "@/lib/utils";
import { SettingsProvider } from "./SettingsProvider";

export function QueryProvider({ children }: { children: ReactNode }) {
  const { userId, isLoaded } = useAuth();
  if (!isLoaded) return null;
  // Remount all personal state and give each identity a separate cache. Late
  // responses from the previous account can only reach its retired client.
  return <QuerySession key={userId ?? "guest"}>{children}</QuerySession>;
}

function QuerySession({ children }: { children: ReactNode }) {
  // Create QueryClient inside useState to avoid recreating on every render
  const [queryClient] = useState(
    () =>
      new QueryClient({
        // One interception layer for AI access gates (#166): any mutation that
        // fails with a pro-required 403 or usage-limit 429 opens the paywall
        // dialog. Call-site onError handlers still run; they use
        // classifyAiGateError/maybeHandleAiGateError to skip generic toasts.
        // Hooks without their own error UI opt into a toast via
        // `meta: { errorMessage }` so a failed save is never silent.
        mutationCache: new MutationCache({
          onError: (error, _variables, _context, mutation) => {
            if (maybeHandleAiGateError(error)) return;
            const fallback = mutation.meta?.errorMessage;
            if (typeof fallback === "string") {
              toast.error(getErrorMessage(error, fallback));
            }
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
            refetchOnReconnect: true,
          },
          mutations: {
            // A lost response does not mean the write failed. Toggle/create/AI
            // operations must never be repeated automatically.
            retry: false,
          },
        },
      })
  );

  useEffect(() => () => {
    void queryClient.cancelQueries();
    queryClient.clear();
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}><SettingsProvider>{children}</SettingsProvider></QueryClientProvider>
  );
}
