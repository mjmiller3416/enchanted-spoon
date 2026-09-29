"use client";

import { useMemo, useState } from "react";
import {
  ArrowDown,
  BookOpen,
  ChefHat,
  TrendingUp,
  UserCheck,
  UserPlus,
  Users,
} from "lucide-react";
import { QueryError } from "@/components/common/QueryError";
import { StatCard } from "@/components/common/StatCard";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, formatRelativeTime } from "@/lib/utils";
import { SectionHeader } from "./SectionHeader";
import { getTierBadge } from "./AdminUsageSection";
import { useAdminActivity } from "@/hooks/api";
import type { AdminUserActivity } from "@/types/admin";

// ── Sorting ──────────────────────────────────────────────────────────────────

type SortKey =
  | "last_active_at"
  | "created_at"
  | "recipes"
  | "favorites"
  | "collections"
  | "saved_meals"
  | "planned_meals"
  | "meals_cooked"
  | "shopping_items";

function sortValue(user: AdminUserActivity, key: SortKey): number {
  const value = user[key];
  if (typeof value === "number") return value;
  // Never-seen users sink to the bottom of a descending date sort
  return value ? new Date(value).getTime() : -Infinity;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ── Sortable header ──────────────────────────────────────────────────────────

function SortHead({
  label,
  sortKey,
  active,
  onSort,
  align = "right",
}: {
  label: string;
  sortKey: SortKey;
  active: SortKey;
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}) {
  const isActive = active === sortKey;
  return (
    <TableHead
      className={cn(align === "right" && "text-right")}
      aria-sort={isActive ? "descending" : "none"}
    >
      <Button
        variant="ghost"
        size="xs"
        onClick={() => onSort(sortKey)}
        className={cn(
          "-mx-2 font-medium",
          isActive ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        {isActive && <ArrowDown className="size-3" strokeWidth={1.5} />}
      </Button>
    </TableHead>
  );
}

// ── Count cell with optional secondary line ──────────────────────────────────

function CountCell({ value, detail }: { value: number; detail?: string }) {
  return (
    <TableCell className="text-right tabular-nums">
      <p className={cn(value === 0 && "text-muted-foreground")}>
        {value.toLocaleString()}
      </p>
      {detail && <p className="text-xs text-muted-foreground whitespace-nowrap">{detail}</p>}
    </TableCell>
  );
}

function recipeDetail(user: AdminUserActivity): string | undefined {
  const parts = [
    user.recipes_ai_generated > 0 && `${user.recipes_ai_generated} AI`,
    user.recipes_imported > 0 && `${user.recipes_imported} imported`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : undefined;
}

const ACTIVITY_COLUMN_COUNT = 10;

export function AdminActivitySection() {
  const [sortKey, setSortKey] = useState<SortKey>("last_active_at");
  const { data, isLoading, isError, isFetching, refetch } = useAdminActivity();

  const users = useMemo(
    () =>
      [...(data?.users ?? [])].sort(
        (a, b) => sortValue(b, sortKey) - sortValue(a, sortKey),
      ),
    [data, sortKey],
  );

  const windowDays = data?.window_days ?? 30;
  const summary = data?.summary;
  const headProps = { active: sortKey, onSort: setSortKey };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard icon={Users} value={summary?.total_users ?? 0} label="Total users" colorClass="purple" isLoading={isLoading} compact />
        <StatCard icon={UserCheck} value={summary?.active_7d ?? 0} label="Active, last 7 days" colorClass="green" isLoading={isLoading} compact />
        <StatCard icon={TrendingUp} value={summary?.active_30d ?? 0} label={`Active, last ${windowDays} days`} colorClass="teal" isLoading={isLoading} compact />
        <StatCard icon={UserPlus} value={summary?.new_users_30d ?? 0} label={`New, last ${windowDays} days`} colorClass="indigo" isLoading={isLoading} compact />
        <StatCard icon={BookOpen} value={summary?.recipes_recent ?? 0} label={`Recipes added, ${windowDays}d`} colorClass="amber" isLoading={isLoading} compact />
        <StatCard icon={ChefHat} value={summary?.meals_cooked_recent ?? 0} label={`Meals cooked, ${windowDays}d`} colorClass="pink" isLoading={isLoading} compact />
      </div>

      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={TrendingUp}
            title="User Activity"
            description="What each user has built and done. Starter-pack recipes and meals are excluded. Select a column to sort."
          />

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
            <QueryError title="Couldn’t load activity" onRetry={() => void refetch()} retrying={isFetching} />
          ) : (
            <div className="min-w-0 rounded-lg border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <SortHead label="Last active" sortKey="last_active_at" align="left" {...headProps} />
                    <SortHead label="Joined" sortKey="created_at" align="left" {...headProps} />
                    <SortHead label="Recipes" sortKey="recipes" {...headProps} />
                    <SortHead label="Favorites" sortKey="favorites" {...headProps} />
                    <SortHead label="Collections" sortKey="collections" {...headProps} />
                    <SortHead label="Saved meals" sortKey="saved_meals" {...headProps} />
                    <SortHead label="Planned" sortKey="planned_meals" {...headProps} />
                    <SortHead label="Cooked" sortKey="meals_cooked" {...headProps} />
                    <SortHead label="Shopping" sortKey="shopping_items" {...headProps} />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
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
                      <TableCell className="whitespace-nowrap">
                        {user.last_active_at ? (
                          <span title={new Date(user.last_active_at).toLocaleString()}>
                            {formatRelativeTime(user.last_active_at)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">Not yet seen</span>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-muted-foreground">
                        {formatDate(user.created_at)}
                      </TableCell>
                      <CountCell
                        value={user.recipes}
                        detail={recipeDetail(user)}
                      />
                      <CountCell value={user.favorites} />
                      <CountCell value={user.collections} />
                      <CountCell value={user.saved_meals} />
                      <CountCell value={user.planned_meals} />
                      <CountCell
                        value={user.meals_cooked}
                        detail={
                          user.last_cooked_at
                            ? `${user.meals_cooked_recent} in ${windowDays}d`
                            : undefined
                        }
                      />
                      <CountCell value={user.shopping_items} />
                    </TableRow>
                  ))}

                  {users.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={ACTIVITY_COLUMN_COUNT}
                        className="text-center text-sm text-muted-foreground py-8"
                      >
                        No users yet.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
