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

/**
 * Shown when #210's account API says `is_read_only`. Writes are rejected
 * there; this banner explains that and offers a subscription again.
 */
export function ReadOnlyBanner() {
  const { data: user } = useCurrentUser();
  const [open, setOpen] = useState(false);
  const startCheckout = useStartCheckout();
  if (!user?.is_read_only) return null;

  const native = isNativeApp();

  const start = () => {
    startCheckout.mutate(undefined, {
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
                  Continue to web checkout to subscribe. Plan prices and the trial are handled there.
                </DialogDescription>
              </DialogHeader>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button onClick={start} disabled={startCheckout.isPending}>
                  {startCheckout.isPending && (
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                  )}
                  Continue to checkout
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
