"use client";

import { useMemo, useState } from "react";
import { Activity, ChevronLeft, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { SectionHeader } from "./SectionHeader";
import { useAdminUsage } from "@/hooks/api";
import type { AdminUserUsage } from "@/types/admin";

// ── Month helpers (UTC-based to match the server default) ────────────────────

function getCurrentMonth(): string {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = String(now.getUTCMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function shiftMonth(month: string, delta: number): string {
  const [year, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(year, m - 1 + delta, 1));
  const nextYear = d.getUTCFullYear();
  const nextMonth = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${nextYear}-${nextMonth}`;
}

function formatMonthLabel(month: string): string {
  const [year, m] = month.split("-").map(Number);
  return new Date(Date.UTC(year, m - 1, 1)).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

// ── Tier badge (mirrors AdminUsersSection.getAccessBadge) ────────────────────

function getTierBadge(user: AdminUserUsage) {
  if (user.is_admin) {
    return (
      <Badge variant="default" size="sm">
        Admin
      </Badge>
    );
  }
  if (user.has_pro_access) {
    return (
      <Badge variant="secondary" size="sm">
        Pro
      </Badge>
    );
  }
  return (
    <Badge variant="outline" size="sm">
      {user.subscription_tier || "Free"}
    </Badge>
  );
}

// ── Usage cell: "used / limit" with threshold coloring ───────────────────────

function UsageCell({ used, limit }: { used: number; limit: number | null }) {
  const isOverLimit = limit !== null && used >= limit;
  const isNearLimit = limit !== null && !isOverLimit && used >= limit * 0.8;
  const limitLabel = limit === null ? "∞" : limit.toLocaleString();

  return (
    <TableCell
      className={cn(
        "text-right tabular-nums",
        isOverLimit && "text-destructive font-medium",
        isNearLimit && "text-warning font-medium",
      )}
    >
      {used.toLocaleString()} / {limitLabel}
    </TableCell>
  );
}

const USAGE_COLUMN_COUNT = 5;

export function AdminUsageSection() {
  const [month, setMonth] = useState<string>(getCurrentMonth);
  const currentMonth = useMemo(() => getCurrentMonth(), []);
  const isCurrentMonth = month >= currentMonth;

  const { data, isLoading, isError, error } = useAdminUsage(month);

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <SectionHeader
            icon={Activity}
            title="AI Usage"
            description="AI feature usage and limits per user, by month."
          />

          {/* Month navigation */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              size="icon"
              variant="outline"
              aria-label="Previous month"
              onClick={() => setMonth((m) => shiftMonth(m, -1))}
            >
              <ChevronLeft className="size-4" strokeWidth={1.5} />
            </Button>
            <span className="text-sm font-medium text-foreground text-center min-w-36">
              {formatMonthLabel(month)}
            </span>
            <Button
              size="icon"
              variant="outline"
              aria-label="Next month"
              disabled={isCurrentMonth}
              onClick={() => setMonth((m) => shiftMonth(m, 1))}
            >
              <ChevronRight className="size-4" strokeWidth={1.5} />
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-56" />
                </div>
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <p className="text-sm text-destructive text-center py-8">
            {error instanceof Error
              ? error.message
              : "Failed to load usage data."}
          </p>
        ) : (
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead className="text-right">Images</TableHead>
                  <TableHead className="text-right">Suggestions</TableHead>
                  <TableHead className="text-right">Assistant Msgs</TableHead>
                  <TableHead className="text-right">Imports</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.users.map((user) => (
                  <TableRow key={user.user_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">
                            {user.name || "No name"}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            {user.email}
                          </p>
                        </div>
                        {getTierBadge(user)}
                      </div>
                    </TableCell>
                    <UsageCell
                      used={user.ai_images_generated}
                      limit={user.limits.ai_images_generated}
                    />
                    <UsageCell
                      used={user.ai_suggestions_requested}
                      limit={user.limits.ai_suggestions_requested}
                    />
                    <UsageCell
                      used={user.ai_assistant_messages}
                      limit={user.limits.ai_assistant_messages}
                    />
                    <UsageCell
                      used={user.recipes_imported}
                      limit={user.limits.recipes_imported}
                    />
                  </TableRow>
                ))}

                {data && data.users.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={USAGE_COLUMN_COUNT}
                      className="text-center text-sm text-muted-foreground py-8"
                    >
                      No usage recorded for this month.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
