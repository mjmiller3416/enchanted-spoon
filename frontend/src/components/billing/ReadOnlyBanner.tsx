"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ProPaywall } from "@/components/billing/ProPaywall";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCurrentUser, useStartCheckout } from "@/hooks/api";
import { isNativeApp } from "@/lib/native/platform";
import { PRO_ANNUAL_PRICE_LABEL, PRO_MONTHLY_PRICE_LABEL } from "@/lib/pro-plans";

/**
 * Shown when the account API says access_mode is read-only. Writes are
 * rejected by the backend; this banner is how the app explains that and
 * offers a subscription again.
 */
export function ReadOnlyBanner() {
  const { data: user } = useCurrentUser();
  const [open, setOpen] = useState(false);
  const startCheckout = useStartCheckout();
  if (user?.access_mode !== "read_only") return null;

  const native = isNativeApp();

  const start = (interval: "month" | "year") => {
    startCheckout.mutate(interval, {
      onError: (error) =>
        toast.error(error instanceof Error && error.message ? error.message : "Couldn't start checkout."),
    });
  };

  return (
    <>
      <div className="border-b border-border bg-muted px-4 py-3 print:hidden">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-foreground">
            Your account is view-only. You can still open recipes and export your data.
            Subscribe to Pro to add and edit again.
          </p>
          <Button onClick={() => setOpen(true)} className="shrink-0">
            Subscribe to Pro
          </Button>
        </div>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent size="lg" className="max-h-screen overflow-y-auto">
          {native ? (
            <ProPaywall
              onClose={() => setOpen(false)}
              trialAvailable={!user.trial_consumed}
            />
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>Subscribe to Pro</DialogTitle>
                <DialogDescription>
                  {PRO_MONTHLY_PRICE_LABEL}/month or {PRO_ANNUAL_PRICE_LABEL}/year. A 7-day free
                  trial applies if this account hasn&apos;t used one.
                </DialogDescription>
              </DialogHeader>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button onClick={() => start("year")} disabled={startCheckout.isPending}>
                  {startCheckout.isPending && (
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                  )}
                  Annual — {PRO_ANNUAL_PRICE_LABEL}/yr
                </Button>
                <Button variant="outline" onClick={() => start("month")} disabled={startCheckout.isPending}>
                  Monthly — {PRO_MONTHLY_PRICE_LABEL}/mo
                </Button>
                <Button variant="outline" onClick={() => setOpen(false)}>
                  Close
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
