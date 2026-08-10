"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
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

/**
 * Upgrade prompt for AI access gates (#166). Opens when any AI call fails
 * with a pro-required 403 or a usage-limit 429 (see lib/paywall.ts).
 *
 * Free users get an upgrade CTA; pro users hitting their (anti-abuse) cap
 * just get a plain "resets next month" notice.
 */
export function PaywallDialog() {
  const [event, setEvent] = useState<PaywallEvent | null>(null);
  const { data: currentUser } = useCurrentUser();
  const startCheckout = useStartCheckout();

  useEffect(() => subscribePaywall(setEvent), []);

  const isPro = currentUser?.has_pro_access ?? false;
  const isLimit = event?.reason === "limit_reached";
  const showUsage = isLimit && event?.limit != null && event?.current != null;

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

  const title = !isLimit
    ? "This is a Pro feature"
    : isPro
      ? "Monthly limit reached"
      : "You've used this month's free allowance";

  const description = !isLimit
    ? "AI-powered features — importing recipes from a URL, generating images, and the Genie assistant — are part of Whiskful Pro."
    : isPro
      ? `You've hit this month's cap for ${event?.featureLabel}. It resets at the start of next month.`
      : `The free plan includes a taste of every AI feature. You've used this month's allowance for ${event?.featureLabel} — it resets at the start of next month.`;

  return (
    <Dialog open={event !== null} onOpenChange={(open) => !open && setEvent(null)}>
      <DialogContent className="sm:max-w-md">
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

        <DialogFooter className="gap-2 sm:gap-2">
          {isPro ? (
            <Button onClick={() => setEvent(null)}>Got it</Button>
          ) : (
            <>
              <Button variant="outline" asChild>
                <Link href="/pricing" onClick={() => setEvent(null)}>
                  See plans
                </Link>
              </Button>
              <Button onClick={handleUpgrade} disabled={startCheckout.isPending}>
                {startCheckout.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                )}
                Upgrade to Pro — $4.99/mo
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
