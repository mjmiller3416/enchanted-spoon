"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { billingApi } from "@/lib/api";
import { useCurrentUser, useStartCheckout } from "@/hooks/api";
import { currentUserQueryKeys } from "@/hooks/api/queryKeys";

function spotsLine(label: string, remaining: number | null, total: number | null): string | null {
  if (remaining == null || remaining <= 0 || total == null) return null;
  return `${label}: ${remaining} of ${total} left`;
}

/**
 * Banner plus one-time pop-up for legacy free accounts, and a read-only
 * notice after the free plan ends.
 */
export function FreePlanNotice() {
  const { data: user } = useCurrentUser();
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const startCheckout = useStartCheckout();
  const [open, setOpen] = useState(true);
  const offer = useQuery({
    queryKey: ["founder-offer"],
    queryFn: () => billingApi.founderOffer(),
    enabled: !!user?.show_sunset_banner,
    staleTime: 60_000,
  });
  const dismiss = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      await billingApi.dismissSunsetNotice(token);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: currentUserQueryKeys.all });
      setOpen(false);
    },
  });

  if (!user?.show_sunset_banner && !user?.is_read_only) return null;

  const monthlySpots = spotsLine(
    "FOUNDER30",
    offer.data?.monthly.spots_remaining ?? null,
    offer.data?.monthly.spots_total ?? null,
  );
  const annualSpots = spotsLine(
    "FOUNDER30Y",
    offer.data?.annual.spots_remaining ?? null,
    offer.data?.annual.spots_total ?? null,
  );
  const spots = [monthlySpots, annualSpots].filter(Boolean).join(". ");

  const claim = () => {
    startCheckout.mutate(
      { plan: "monthly", promotionCode: "FOUNDER30" },
      { onError: (error) => toast.error(error.message || "Couldn't start checkout.") },
    );
  };

  return (
    <>
      <div className="border-b border-border bg-muted px-4 py-3 text-sm text-foreground">
        <div className="mx-auto flex max-w-5xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p>
            {user.is_read_only
              ? "Your free plan is now read-only. You can view and export everything you've saved. Creating, planning, and AI need Pro."
              : "Free plan ends Mar 31, 2027. Keep everything you've saved: start a 7-day Pro trial, or go read-only. Founding members save with FOUNDER30 or FOUNDER30Y."}
            {spots ? ` ${spots}.` : ""}
          </p>
          {!user.has_pro_access && (
            <Button size="sm" onClick={claim} disabled={startCheckout.isPending}>
              {startCheckout.isPending && <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />}
              See options
            </Button>
          )}
        </div>
      </div>

      <Dialog open={!!user.show_sunset_popup && open} onOpenChange={(next) => !next && dismiss.mutate()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Changes to the free plan</DialogTitle>
            <DialogDescription>
              On Mar 31, 2027 at 11:59 PM ET, free accounts become read-only. You can still view and export all your recipes, plans and lists, but creating, planning and AI will need Pro. Start a 7-day free trial on the web with code FOUNDER30 for 30% off your first 3 months ($4.89/mo), or FOUNDER30Y for a $39.99 first year.
              {spots ? ` Founding spots: ${spots}.` : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => dismiss.mutate()} disabled={dismiss.isPending}>
              Remind me later
            </Button>
            <Button onClick={claim} disabled={startCheckout.isPending}>
              Claim founding price on the web
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
