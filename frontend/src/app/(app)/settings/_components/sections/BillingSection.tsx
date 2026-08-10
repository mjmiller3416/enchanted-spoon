"use client";

import { CreditCard, ExternalLink, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { SectionHeader } from "../SectionHeader";
import {
  useCurrentUser,
  useMyUsage,
  useOpenBillingPortal,
  useStartCheckout,
} from "@/hooks/api";
import type { CurrentUserDTO } from "@/types/admin";
import type { CurrentUserUsage } from "@/types/billing";

const USAGE_ROWS: {
  field: keyof Pick<
    CurrentUserUsage,
    | "ai_images_generated"
    | "ai_suggestions_requested"
    | "ai_assistant_messages"
    | "recipes_imported"
  >;
  label: string;
}[] = [
  { field: "recipes_imported", label: "Recipe imports" },
  { field: "ai_suggestions_requested", label: "AI suggestions" },
  { field: "ai_images_generated", label: "AI images" },
  { field: "ai_assistant_messages", label: "Assistant messages" },
];

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function planBadge(user: CurrentUserDTO) {
  if (user.is_admin) return <Badge variant="default">Admin</Badge>;
  if (user.has_pro_access) return <Badge variant="secondary">Pro</Badge>;
  return <Badge variant="outline">Free</Badge>;
}

function planDetail(user: CurrentUserDTO): string {
  if (user.is_admin) {
    return "Admin accounts have unlimited access to everything.";
  }
  if (user.access_reason === "subscription") {
    if (user.subscription_status === "past_due") {
      return "Payment past due — update your payment method to keep Pro access.";
    }
    if (user.subscription_ends_at) {
      return `Your Pro subscription renews on ${formatDate(user.subscription_ends_at)}.`;
    }
    return "Your Pro subscription is active.";
  }
  if (user.has_pro_access) {
    return "You have complimentary Pro access.";
  }
  return "The free plan includes all core features and a monthly taste of every AI feature.";
}

function UsageRow({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number | null;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground">{label}</span>
        {limit === null ? (
          <span className="text-muted-foreground">Unlimited</span>
        ) : (
          <span className="text-muted-foreground">
            {used} / {limit}
          </span>
        )}
      </div>
      {limit !== null && (
        <Progress
          value={limit > 0 ? Math.min(100, (used / limit) * 100) : 100}
          aria-label={`${label}: ${used} of ${limit} used`}
        />
      )}
    </div>
  );
}

/**
 * Settings → Plan & Billing: current plan, upgrade/manage-billing actions,
 * and the monthly AI usage meter.
 */
export function BillingSection() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: usage, isLoading: usageLoading } = useMyUsage();
  const startCheckout = useStartCheckout();
  const openPortal = useOpenBillingPortal();

  const handleUpgrade = () => {
    startCheckout.mutate(undefined, {
      onError: (error) =>
        toast.error(error.message || "Couldn't start checkout. Please try again."),
    });
  };

  const handleManageBilling = () => {
    openPortal.mutate(undefined, {
      onError: (error) =>
        toast.error(error.message || "Couldn't open the billing portal. Please try again."),
    });
  };

  const showUpgrade = !!user && !user.has_pro_access;
  const showManageBilling = !!user && user.subscription_tier === "pro" && !user.is_admin;

  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={CreditCard}
          title="Plan & Billing"
          description="Your subscription and monthly AI usage"
        />

        <div className="space-y-6">
          {/* Current plan */}
          {userLoading || !user ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-64" />
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">Current plan</span>
                {planBadge(user)}
              </div>
              <p className="text-sm text-muted-foreground">{planDetail(user)}</p>

              <div className="flex flex-wrap items-center gap-2 pt-1">
                {showUpgrade && (
                  <Button onClick={handleUpgrade} disabled={startCheckout.isPending} className="gap-2">
                    {startCheckout.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    ) : (
                      <Sparkles className="h-4 w-4" strokeWidth={1.5} />
                    )}
                    Upgrade to Pro — $4.99/mo
                  </Button>
                )}
                {showManageBilling && (
                  <Button
                    variant="outline"
                    onClick={handleManageBilling}
                    disabled={openPortal.isPending}
                    className="gap-2"
                  >
                    {openPortal.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    ) : (
                      <ExternalLink className="h-4 w-4" strokeWidth={1.5} />
                    )}
                    Manage billing
                  </Button>
                )}
              </div>
            </div>
          )}

          <Separator />

          {/* Usage meter */}
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-foreground">AI usage this month</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Counters reset at the start of each month.
              </p>
            </div>

            {usageLoading || !usage ? (
              <div className="space-y-4">
                {USAGE_ROWS.map((row) => (
                  <div key={row.field} className="space-y-1.5">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {USAGE_ROWS.map((row) => (
                  <UsageRow
                    key={row.field}
                    label={row.label}
                    used={usage[row.field]}
                    limit={usage.limits[row.field]}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
