"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { WebFoundingOffer } from "@/components/billing/WebFoundingOffer";
import { Button } from "@/components/ui/button";
import { billingApi } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";
import { useQueryClient } from "@tanstack/react-query";
import { currentUserQueryKeys } from "@/hooks/api/queryKeys";
import { appConfig } from "@/lib/config";
import { nativePlatform } from "@/lib/native/platform";
import {
  NativePurchasesUnavailableError,
  purchasePlan,
  restorePurchases,
} from "@/lib/native/purchases";
import {
  PRO_ANNUAL_PRICE_LABEL,
  PRO_MONTHLY_PRICE_LABEL,
  PRO_TRIAL_DAYS,
  billingDate,
  formatBillingDate,
  type ProInterval,
} from "@/lib/pro-plans";
import { cn } from "@/lib/utils";

interface ProPaywallProps {
  onClose: () => void;
  trialAvailable: boolean;
  /** Localized store prices, when StoreKit or Play Billing returned them. */
  monthlyPriceLabel?: string;
  annualPriceLabel?: string;
}

/**
 * Subscription screen used inside the native shell.
 * Meets App Store Guideline 3.1.2: plan name, length, price, billing date,
 * a visible Close control, Restore Purchases, and links to the privacy
 * policy and Terms of Use.
 */
export function ProPaywall({
  onClose,
  trialAvailable,
  monthlyPriceLabel = PRO_MONTHLY_PRICE_LABEL,
  annualPriceLabel = PRO_ANNUAL_PRICE_LABEL,
}: ProPaywallProps) {
  const [interval, setInterval] = useState<ProInterval>("year");
  const [pending, setPending] = useState<"purchase" | "restore" | null>(null);
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const price = interval === "year" ? annualPriceLabel : monthlyPriceLabel;
  const length = interval === "year" ? "1 year" : "1 month";
  const period = interval === "year" ? "year" : "month";
  const chargeDate = formatBillingDate(billingDate(new Date(), trialAvailable));
  const platform = nativePlatform();
  const storeName = platform === "android" ? "Google Play" : "the App Store";

  const syncAndRefresh = async () => {
    const token = await getToken();
    try {
      await billingApi.syncStoreEntitlement(token);
    } catch {
      // The webhook can still grant access if this confirmation is unavailable.
    }
    await queryClient.invalidateQueries({ queryKey: currentUserQueryKeys.all });
  };

  const handlePurchase = async () => {
    setPending("purchase");
    try {
      await purchasePlan(interval);
      await syncAndRefresh();
      toast.success("You're subscribed to Pro.");
      onClose();
    } catch (error) {
      if (error instanceof NativePurchasesUnavailableError) {
        toast.error(error.message);
        return;
      }
      const message = error instanceof Error ? error.message : "";
      if (message.toLowerCase().includes("cancel")) return;
      toast.error(message || "Couldn't complete the purchase. Please try again.");
    } finally {
      setPending(null);
    }
  };

  const handleRestore = async () => {
    setPending("restore");
    try {
      await restorePurchases();
      await syncAndRefresh();
      toast.success("Purchases restored. If a subscription is active, Pro unlocks in a moment.");
    } catch (error) {
      if (error instanceof NativePurchasesUnavailableError) {
        toast.error(error.message);
        return;
      }
      toast.error(
        error instanceof Error && error.message
          ? error.message
          : "Couldn't restore purchases. Please try again.",
      );
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1 pr-8">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
          <Sparkles className="h-5 w-5 text-primary" strokeWidth={1.5} />
          {appConfig.appName} Pro
        </h2>
        <p className="text-sm text-muted-foreground">
          Recipes, planning, and shopping stay free. AI — import, generation,
          photos, and Genie — starts with a 7-day trial. There is no free AI
          allowance on accounts created at or after the release.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <PlanOption
          selected={interval === "year"}
          title="Annual"
          price={annualPriceLabel}
          cadence="per year"
          detail="1 year, auto-renewable"
          badge="Best value"
          onSelect={() => setInterval("year")}
        />
        <PlanOption
          selected={interval === "month"}
          title="Monthly"
          price={monthlyPriceLabel}
          cadence="per month"
          detail="1 month, auto-renewable"
          onSelect={() => setInterval("month")}
        />
      </div>

      {trialAvailable ? (
        <ol className="flex flex-col gap-2 text-sm text-muted-foreground">
          <li>
            <span className="font-medium text-foreground">Today.</span> Full Pro access starts.
            You won&apos;t be charged.
          </li>
          <li>
            <span className="font-medium text-foreground">
              Day {PRO_TRIAL_DAYS}, {chargeDate}.
            </span>{" "}
            {price} is billed for the {length} plan unless you cancel before then.
          </li>
        </ol>
      ) : (
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{price}</span> for {length}, billed on{" "}
          {chargeDate}. This account already used its free trial.
        </p>
      )}

      <p className="text-sm text-foreground">
        {trialAvailable
          ? `${PRO_TRIAL_DAYS}-day free trial, then ${price} per ${period}.`
          : `${price} per ${period}.`}{" "}
        {appConfig.appName} Pro, {length}. The subscription renews automatically until you cancel
        at least 24 hours before the end of the period. You&apos;re billed by {storeName}. Manage
        or cancel the subscription in your {storeName} account settings.
      </p>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Button onClick={() => void handlePurchase()} disabled={pending !== null} className="flex-1">
          {pending === "purchase" && (
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
          )}
          {trialAvailable ? `Start ${PRO_TRIAL_DAYS}-day free trial` : `Subscribe — ${price}/${period === "year" ? "yr" : "mo"}`}
        </Button>
        <Button
          variant="outline"
          onClick={() => void handleRestore()}
          disabled={pending !== null}
        >
          {pending === "restore" && (
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
          )}
          Restore purchases
        </Button>
        <Button variant="outline" onClick={onClose} disabled={pending !== null}>
          Close
        </Button>
      </div>

      <WebFoundingOffer />

      <p className="text-xs text-muted-foreground">
        <Link href="/privacy" className="font-medium text-primary underline-offset-4 hover:underline">
          Privacy Policy
        </Link>
        {" · "}
        <Link href="/terms" className="font-medium text-primary underline-offset-4 hover:underline">
          Terms of Use
        </Link>
      </p>
    </div>
  );
}

function PlanOption({
  selected,
  title,
  price,
  cadence,
  detail,
  badge,
  onSelect,
}: {
  selected: boolean;
  title: string;
  price: string;
  cadence: string;
  detail: string;
  badge?: string;
  onSelect: () => void;
}) {
  return (
    <Button
      type="button"
      variant="outline"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        "h-auto w-full flex-col items-start gap-1 px-4 py-4 text-left",
        selected && "border-primary",
      )}
    >
      <span className="flex w-full items-center justify-between gap-2">
        <span className="font-medium text-foreground">{title}</span>
        {badge ? <span className="text-xs text-primary">{badge}</span> : null}
      </span>
      <span className="text-base font-semibold text-foreground">
        {price} <span className="text-sm font-normal text-muted-foreground">{cadence}</span>
      </span>
      <span className="text-xs font-normal text-muted-foreground">{detail}</span>
    </Button>
  );
}
