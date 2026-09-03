"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { UtensilsCrossed, ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { CarouselCardGrid } from "./CarouselCardGrid";
import { usePlannerEntries, useMarkComplete } from "@/hooks/api";
import type { PlannerEntryResponseDTO } from "@/types/planner";

// ============================================================================
// CONSTANTS
// ============================================================================

/** Cards per page by viewport — 1 (mobile), 2 (sm), 3 (lg). Matches Tailwind breakpoints. */
const PER_PAGE_DEFAULT = 3;
const PER_PAGE_QUERIES: [query: string, perPage: number][] = [
  ["(min-width: 1024px)", 3],
  ["(min-width: 640px)", 2],
];
const SWIPE_MS = 400;
/** gap-3.5 = 0.875rem = 14px at default 16px root font size */
const GAP_PX = 14;

// ============================================================================
// TYPES
// ============================================================================

interface MealCarouselWidgetProps {
  entries?: PlannerEntryResponseDTO[];
  /** Entry already shown elsewhere (e.g. the Tonight card) — hidden from the grid */
  excludeEntryId?: number | null;
}

interface TransitionState {
  dir: "next" | "prev";
  advance: number;
  prevStartIndex: number;
  stripWidthPx: number;
  fromTxPx: number;
  toTxPx: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/** Pad a slice to always be perPage length (nulls fill empty slots). */
function padPage(
  arr: PlannerEntryResponseDTO[],
  perPage: number
): (PlannerEntryResponseDTO | null)[] {
  return [...arr, ...Array(Math.max(0, perPage - arr.length)).fill(null)];
}

function getPerPage(): number {
  for (const [query, perPage] of PER_PAGE_QUERIES) {
    if (window.matchMedia(query).matches) return perPage;
  }
  return 1;
}

/**
 * Viewport-driven cards-per-page. Starts at the desktop default so SSR and
 * hydration match, then syncs to the real viewport on mount and on resize.
 */
function usePerPage(): number {
  const [perPage, setPerPage] = useState(PER_PAGE_DEFAULT);

  useEffect(() => {
    const mqls = PER_PAGE_QUERIES.map(([query]) => window.matchMedia(query));
    const update = () => setPerPage(getPerPage());
    update();
    mqls.forEach((mql) => mql.addEventListener("change", update));
    return () =>
      mqls.forEach((mql) => mql.removeEventListener("change", update));
  }, []);

  return perPage;
}

// ============================================================================
// MEAL CAROUSEL WIDGET
// ============================================================================

/**
 * MealCarouselWidget — paginated carousel of upcoming meals for the dashboard.
 *
 * Uses startIndex-based sliding window pagination with a dynamic advance amount
 * (1–3 cards per navigation). Animation uses a single extended strip that
 * translates proportionally to the advance — cards that remain visible
 * physically slide to their new positions rather than disappearing/reappearing.
 */
export function MealCarouselWidget({
  entries: initialEntries,
  excludeEntryId = null,
}: MealCarouselWidgetProps) {
  const router = useRouter();
  const perPage = usePerPage();

  // ── Data ──────────────────────────────────────────────────────────────
  const { data: fetchedEntries, isLoading: queryLoading } =
    usePlannerEntries();
  const markComplete = useMarkComplete();

  const entries = useMemo(
    () => initialEntries ?? fetchedEntries ?? [],
    [initialEntries, fetchedEntries]
  );
  const isLoading = !initialEntries && queryLoading;

  const activeEntries = useMemo(
    () =>
      [...entries]
        .sort((a, b) => a.position - b.position)
        .filter((e) => !e.is_completed && e.id !== excludeEntryId),
    [entries, excludeEntryId]
  );

  // Remaining includes the excluded (Tonight) entry so the count stays honest
  const remainingCount = useMemo(
    () => entries.filter((e) => !e.is_completed).length,
    [entries]
  );

  const completedCount = useMemo(
    () => entries.filter((e) => e.is_completed).length,
    [entries]
  );

  const totalMeals = activeEntries.length;

  // ── Carousel State ────────────────────────────────────────────────────
  const [startIndex, setStartIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [completingId, setCompletingId] = useState<number | null>(null);
  const [transition, setTransition] = useState<TransitionState | null>(null);

  const stageRef = useRef<HTMLDivElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);

  // ── Derived Values ────────────────────────────────────────────────────
  // Clamp startIndex when activeEntries shrinks (e.g. meal completion)
  // or perPage grows (e.g. viewport resize)
  const safeStartIndex = Math.min(
    startIndex,
    Math.max(0, totalMeals - perPage)
  );

  const canGoNext = safeStartIndex + perPage < totalMeals;
  const canGoPrev = safeStartIndex > 0;
  const showNav = totalMeals > perPage;

  const currentSlice = padPage(
    activeEntries.slice(safeStartIndex, safeStartIndex + perPage),
    perPage
  );

  // ── Transition Strip ──────────────────────────────────────────────────
  const stripInfo = useMemo(() => {
    if (!transition) return null;

    const { dir, advance, prevStartIndex } = transition;
    const stripLength = perPage + advance;

    const start =
      dir === "next" ? prevStartIndex : prevStartIndex - advance;

    const stripEntries = padPage(
      activeEntries.slice(start, start + stripLength),
      stripLength
    );

    return {
      entries: stripEntries,
      pageOffset: start,
      columns: stripLength,
    };
  }, [transition, activeEntries, perPage]);

  // ── Strip Animation (Web Animations API) ─────────────────────────────
  useEffect(() => {
    if (!transition || !stripRef.current) return;

    const animation = stripRef.current.animate(
      [
        { transform: `translateX(${transition.fromTxPx}px)` },
        { transform: `translateX(${transition.toTxPx}px)` },
      ],
      {
        duration: SWIPE_MS,
        easing: "cubic-bezier(0.4, 0, 0.2, 1)",
        fill: "forwards",
      }
    );

    animation.onfinish = () => {
      setTransition(null);
      setIsAnimating(false);
    };

    return () => animation.cancel();
  }, [transition]);

  // ── Navigation ────────────────────────────────────────────────────────
  const navigate = useCallback(
    (dir: "next" | "prev") => {
      if (isAnimating || !stageRef.current) return;

      const advance =
        dir === "next"
          ? Math.min(perPage, totalMeals - (safeStartIndex + perPage))
          : Math.min(perPage, safeStartIndex);

      if (advance <= 0) return;

      // Measure container for pixel-accurate translation
      const containerWidth = stageRef.current.offsetWidth;
      const slotWidthPx = (containerWidth + GAP_PX) / perPage;
      const stripColumns = perPage + advance;
      const stripWidthPx = stripColumns * slotWidthPx - GAP_PX;

      const fromTxPx = dir === "next" ? 0 : -(advance * slotWidthPx);
      const toTxPx = dir === "next" ? -(advance * slotWidthPx) : 0;

      const prevStartIndex = safeStartIndex;
      const newStartIndex =
        dir === "next"
          ? safeStartIndex + advance
          : safeStartIndex - advance;

      setTransition({
        dir,
        advance,
        prevStartIndex,
        stripWidthPx,
        fromTxPx,
        toTxPx,
      });
      setStartIndex(newStartIndex);
      setIsAnimating(true);
    },
    [isAnimating, safeStartIndex, totalMeals, perPage]
  );

  // ── Actions ───────────────────────────────────────────────────────────
  const handleComplete = useCallback(
    (entryId: number) => {
      setCompletingId(entryId);
      markComplete.mutate(entryId, {
        onSettled: async () => {
          await new Promise((resolve) => setTimeout(resolve, 300));
          setCompletingId(null);
        },
      });
    },
    [markComplete]
  );

  const handleViewRecipe = useCallback(
    (recipeId: number) => {
      router.push(`/recipes/${recipeId}`);
    },
    [router]
  );

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <Card className="flex flex-col px-5 pt-5 pb-3 shadow-raised">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <UtensilsCrossed
            className="size-5 text-secondary"
            strokeWidth={1.5}
          />
          <h2 className="text-lg font-semibold text-foreground">
            Meals This Week
          </h2>
          <span className="text-xs text-muted-foreground">
            {remainingCount} remaining &middot; {completedCount} cooked
          </span>
        </div>
        <Link
          href="/meal-planner"
          className="flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors duration-150"
        >
          View all
          <ArrowRight className="size-4" strokeWidth={1.5} />
        </Link>
      </div>

      {/* ── Content ── */}
      {isLoading ? (
        <CarouselSkeleton />
      ) : activeEntries.length === 0 ? (
        <CarouselEmptyState />
      ) : (
        <>
          {/* Carousel Stage — relative wrapper for nav buttons + card grid */}
          <div ref={stageRef} className="carousel-stage relative h-96">
            {/* Clip zone — clips horizontal swipe overflow, preserves vertical shadows */}
            <div className="absolute inset-0 overflow-x-clip overflow-y-visible">
              {/* Static layer — current visible cards (hidden during animation
                   to prevent them showing through the strip's column gaps) */}
              <CarouselCardGrid
                entries={currentSlice}
                pageOffset={safeStartIndex}
                columns={perPage}
                completingId={completingId}
                onComplete={handleComplete}
                onViewRecipe={handleViewRecipe}
                className={transition ? "opacity-0" : undefined}
              />

              {/* Transition strip — rendered on top during animation */}
              {transition && stripInfo && (
                <CarouselCardGrid
                  ref={stripRef}
                  key={`strip-${transition.prevStartIndex}-${transition.dir}`}
                  entries={stripInfo.entries}
                  pageOffset={stripInfo.pageOffset}
                  columns={stripInfo.columns}
                  completingId={null}
                  onComplete={() => { }}
                  onViewRecipe={() => { }}
                  className="z-10 pointer-events-none"
                  style={{
                    width: `${transition.stripWidthPx}px`,
                    transform: `translateX(${transition.fromTxPx}px)`,
                  }}
                />
              )}
            </div>

            {/* Nav buttons — outside clip zone so they can overlap the edge */}
            {showNav && canGoPrev && (
              <Button
                size="icon-sm"
                shape="pill"
                variant="ghost"
                className="carousel-nav-btn absolute top-1/2 -translate-y-1/2 -left-4 z-20 bg-background/70 backdrop-blur-sm border border-border"
                onClick={() => navigate("prev")}
                disabled={isAnimating}
                aria-label="Previous meals"
              >
                <ChevronLeft className="size-4" strokeWidth={1.5} />
              </Button>
            )}
            {showNav && canGoNext && (
              <Button
                size="icon-sm"
                shape="pill"
                variant="ghost"
                className="carousel-nav-btn absolute top-1/2 -translate-y-1/2 -right-4 z-20 bg-background/70 backdrop-blur-sm border border-border"
                onClick={() => navigate("next")}
                disabled={isAnimating}
                aria-label="Next meals"
              >
                <ChevronRight className="size-4" strokeWidth={1.5} />
              </Button>
            )}
          </div>
        </>
      )}
    </Card>
  );
}

// ============================================================================
// INTERNAL SUB-COMPONENTS
// ============================================================================

/** Loading skeleton — responsive grid of card placeholders (1/2/3 columns). */
function CarouselSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 flex-1">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={cn(
            "flex-col gap-3",
            i === 1 && "flex",
            i === 2 && "hidden sm:flex",
            i === 3 && "hidden lg:flex"
          )}
        >
          <Skeleton className="aspect-video w-full rounded-lg" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <div className="flex-1" />
          <div className="flex gap-2">
            <Skeleton className="h-8 flex-1" />
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Empty state — no active meals in the planner. */
function CarouselEmptyState() {
  return (
    <div className="flex items-center justify-center flex-1 py-8 text-center text-muted-foreground">
      <div className="flex flex-col items-center gap-3">
        <UtensilsCrossed
          className="size-10 text-muted-foreground"
          strokeWidth={1.5}
        />
        <div>
          <p>No more meals planned</p>
          <p className="mt-1 text-sm">Add meals to fill out your week.</p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/meal-planner">Open planner</Link>
        </Button>
      </div>
    </div>
  );
}