"use client";

import { useEffect, useMemo } from "react";
import { useUser } from "@clerk/nextjs";
import { QueryError } from "@/components/common/QueryError";
import { Skeleton } from "@/components/ui/skeleton";
import { PageLayout } from "@/components/layout/PageLayout";
import { PageHeaderContent } from "@/components/layout/PageHeader";
import { MealCarouselWidget } from "./carousel";
import { ShoppingListWidget } from "./ShoppingListWidget";
import { StreakChip } from "./StreakChip";
import { TonightCard } from "./TonightCard";
import { GetStartedCard, GetStartedBanner } from "./GetStartedCard";
import { InstallAppBanner } from "@/components/common/InstallAppBanner";
import { WhatsNewBanner } from "./WhatsNewBanner";
import { useDashboardStats, usePlannerEntries, useShoppingList } from "@/hooks/api";
import { useGetStartedComplete } from "@/hooks/persistence";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/**
 * HomeView — today-first Home for all devices.
 * Tonight hero → shopping status → This Week strip, with a cooking-streak
 * chip in the header and a guided GetStarted flow for brand-new users.
 */
export function HomeView() {
  const { user } = useUser();

  const {
    data: statsData,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
    isFetching: statsFetching,
  } = useDashboardStats();
  const {
    data: plannerEntries,
    isLoading: plannerLoading,
    error: plannerError,
    refetch: refetchPlanner,
    isFetching: plannerFetching,
  } = usePlannerEntries();
  const {
    data: shoppingData,
    isLoading: shoppingLoading,
    error: shoppingError,
    refetch: refetchShopping,
    isFetching: shoppingFetching,
  } = useShoppingList();

  const [setupComplete, setSetupComplete, setupLoaded] = useGetStartedComplete();

  const entries = useMemo(() => plannerEntries ?? [], [plannerEntries]);

  const activeEntries = useMemo(
    () =>
      [...entries]
        .sort((a, b) => a.position - b.position)
        .filter((e) => !e.is_completed),
    [entries]
  );
  const tonight = activeEntries[0] ?? null;
  const completedCount = entries.length - activeEntries.length;

  const totalRecipes = statsData?.total_recipes ?? 0;

  // Once the user has planned a meal, the first-run flow is done for good.
  useEffect(() => {
    if (setupLoaded && !setupComplete && entries.length > 0) {
      setSetupComplete(true);
    }
  }, [setupLoaded, setupComplete, entries.length, setSetupComplete]);

  const dataReady = !statsLoading && !plannerLoading && !statsError && !plannerError && !!statsData;
  const showGetStarted =
    dataReady && totalRecipes === 0 && entries.length === 0;
  const showProgressBanner =
    dataReady &&
    setupLoaded &&
    !setupComplete &&
    totalRecipes > 0 &&
    entries.length === 0;
  // Strip only appears when it has something to show beyond the Tonight card
  const showWeekStrip =
    !plannerLoading &&
    (activeEntries.length > 1 || (completedCount > 0 && entries.length > 0));

  const firstName = user?.firstName || "there";

  // State-aware subtitle — no fake enthusiasm over zeros
  const subtitle = plannerError ? <>Your saved plan will appear when the connection recovers.</> : plannerLoading ? null : activeEntries.length > 0 ? (
    <>
      You have{" "}
      <span className="font-semibold text-primary">{activeEntries.length}</span>{" "}
      meal{activeEntries.length === 1 ? "" : "s"} in your plan.
    </>
  ) : completedCount > 0 ? (
    <>
      All caught up —{" "}
      <span className="font-semibold text-primary">{completedCount}</span> meal
      {completedCount === 1 ? "" : "s"} marked complete.
    </>
  ) : (
    <>Let&apos;s plan your next meal.</>
  );


  return (
    <PageLayout
      headerContent={
        <PageHeaderContent>
          <div className="flex flex-1 flex-col gap-1.5">
            <h1 className="text-page-title text-foreground">
              {`${getGreeting()}, ${firstName} 👋`}
            </h1>
            {subtitle ? (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            ) : (
              <Skeleton className="h-5 w-64" />
            )}
          </div>

          {/* Cooking streak — the header's motivational element, all viewports */}
          <StreakChip />
        </PageHeaderContent>
      }
      contentClassName="flex flex-col"
    >
      {statsError && <div className="mb-4"><QueryError title="Couldn’t refresh your recipe summary" onRetry={() => void refetchStats()} retrying={statsFetching} /></div>}
      {showGetStarted ? (
        <GetStartedCard
          recipesDone={totalRecipes > 0}
          planDone={entries.length > 0}
        />
      ) : (
        <>
          {showProgressBanner && (
            <div className="mb-6 shrink-0">
              <GetStartedBanner />
            </div>
          )}

          <WhatsNewBanner className="mb-6 shrink-0" />
          <InstallAppBanner context="home" className="mb-6 shrink-0" />

          {/* Tonight hero + shopping status */}
          <div
            className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3 lg:gap-6"
            data-tour={dataReady ? "home-overview" : undefined}
          >
            <div className="lg:col-span-2">
              {plannerError && <div className="mb-4"><QueryError title="Couldn’t refresh your meal plan" onRetry={() => void refetchPlanner()} retrying={plannerFetching} /></div>}
              {(!plannerError || plannerEntries) && <TonightCard entry={tonight} isLoading={plannerLoading} />}
            </div>
            <div>
              {shoppingError && <div className="mb-4"><QueryError title="Couldn’t refresh your shopping list" onRetry={() => void refetchShopping()} retrying={shoppingFetching} /></div>}
              {(!shoppingError || shoppingData) && <ShoppingListWidget shoppingData={shoppingData} isLoading={shoppingLoading} />}
            </div>
          </div>

          {/* This Week strip */}
          {showWeekStrip && (
            <div className="mt-6 shrink-0">
              <MealCarouselWidget
                entries={entries}
                excludeEntryId={tonight?.id ?? null}
              />
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
