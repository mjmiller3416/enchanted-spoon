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
import { PRO_ANNUAL_PRICE_LABEL, PRO_MONTHLY_PRICE_LABEL } from "@/lib/pro-plans";

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

  const handleUpgrade = (interval: "month" | "year") => {
    startCheckout.mutate(interval, {
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

  const description = isReadOnly
    ? "You can still view and export your recipes. Subscribe to Pro to add and edit again."
    : !isLimit
      ? `AI-powered features — importing recipes from a URL, generating images, and the Genie assistant — are part of ${appConfig.appName} Pro.`
      : isPro
        ? `You've hit this month's cap for ${event?.featureLabel}. It resets at the start of next month.`
        : `The free plan includes a taste of every AI feature. You've used this month's allowance for ${event?.featureLabel} — it resets at the start of next month.`;

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
                  <Button onClick={() => handleUpgrade("year")} disabled={startCheckout.isPending}>
                    {startCheckout.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    )}
                    Annual — {PRO_ANNUAL_PRICE_LABEL}/yr
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => handleUpgrade("month")}
                    disabled={startCheckout.isPending}
                  >
                    Monthly — {PRO_MONTHLY_PRICE_LABEL}/mo
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
