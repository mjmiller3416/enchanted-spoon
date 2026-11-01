"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { ProPaywall } from "@/components/billing/ProPaywall";
import { WebFoundingOffer } from "@/components/billing/WebFoundingOffer";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCurrentUser, useStartCheckout } from "@/hooks/api";
import { subscribePaywall, type PaywallEvent } from "@/lib/paywall";
import { appConfig } from "@/lib/config";
import { isNativeApp } from "@/lib/native/platform";

/**
 * Upgrade prompt for AI access gates and for a view-only account.
 * Inside the native shell the Stripe checkout buttons are replaced by the
 * store paywall.
 */
export function PaywallDialog() {
  const [event, setEvent] = useState<PaywallEvent | null>(null);
  const { data: currentUser } = useCurrentUser();
  const startCheckout = useStartCheckout();
  const [native, setNative] = useState(false);

  useEffect(() => subscribePaywall(setEvent), []);
  useEffect(() => setNative(isNativeApp()), []);

  const isPro = currentUser?.has_pro_access ?? false;
  const isLimit = event?.reason === "limit_reached";
  const isReadOnly = event?.reason === "read_only";
  const showUsage = isLimit && event?.limit != null && event?.current != null;
  const showStorePaywall = native && !isPro && event !== null;

  const handleUpgrade = () => {
    startCheckout.mutate(undefined, {
      onError: (error) =>
        toast.error(
          error instanceof Error && error.message
            ? error.message
            : "Couldn't start checkout. Please try again.",
        ),
    });
  };

  const title = isReadOnly
    ? "Your account is view-only"
    : !isLimit
      ? "This is a Pro feature"
      : isPro
        ? "Monthly limit reached"
        : "You've used this month's free allowance";

  const legacyFreeAllowance = currentUser?.usage_tier === "free";
  const description = isReadOnly
    ? "You can still view and export your recipes. Subscribe to Pro to add and edit again."
    : !isLimit
      ? `AI features are part of ${appConfig.appName} Pro. In the app, the first one starts a 7-day trial. Recipes, planning, and shopping stay free.`
      : isPro
        ? `You've hit this month's cap for ${event?.featureLabel}. It resets at the start of next month.`
        : legacyFreeAllowance
          ? `You've used this month's free allowance for ${event?.featureLabel}. It resets at the start of next month, or you can start a 7-day trial.`
          : `This account doesn't include a free AI allowance. A 7-day trial unlocks ${event?.featureLabel}. Recipes, planning, and shopping stay free.`;

  return (
    <Dialog open={event !== null} onOpenChange={(open) => !open && setEvent(null)}>
      <DialogContent size={showStorePaywall ? "lg" : "sm"} className="max-h-screen overflow-y-auto">
        {showStorePaywall ? (
          <ProPaywall
            onClose={() => setEvent(null)}
            trialAvailable={!currentUser?.trial_consumed}
          />
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" strokeWidth={1.5} />
                {title}
              </DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </DialogHeader>

            {showUsage && (
              <p className="text-sm text-muted-foreground">
                Used this month:{" "}
                <span className="font-medium text-foreground">
                  {event?.current}/{event?.limit}
                </span>
              </p>
            )}

            {!isPro && <WebFoundingOffer />}

            <DialogFooter className="gap-2 sm:gap-2">
              {isPro ? (
                <Button onClick={() => setEvent(null)}>Got it</Button>
              ) : (
                <>
                  <Button variant="outline" onClick={() => setEvent(null)}>
                    Close
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href="/pricing" onClick={() => setEvent(null)}>
                      See plans
                    </Link>
                  </Button>
                  <Button onClick={handleUpgrade} disabled={startCheckout.isPending}>
                    {startCheckout.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    )}
                    Upgrade to Pro
                  </Button>
                </>
              )}
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
