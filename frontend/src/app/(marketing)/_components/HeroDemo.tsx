"use client";

import * as React from "react";
import Image from "next/image";
import { CalendarDays, Plus, ShoppingCart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  FRIDAY_NIGHT,
  GROCERY_LIST,
  LIST_TOTAL_AFTER,
  LIST_TOTAL_BEFORE,
  PLANNED_WEEK,
  SHRIMP_PASTA,
  type ListItem,
  type PlannedNight,
} from "./examples";

const FIRST_ADD_MS = 1400;
const HOLD_ADDED_MS = 5200;
const HOLD_EMPTY_MS = 1800;

/**
 * The hero's "aha" moment: a dinner lands on Friday and the grocery list
 * updates — new items appear and shared ingredients combine.
 *
 * The server renders Friday empty. After hydration the loop plays; under
 * prefers-reduced-motion it skips straight to the finished state.
 */
export function HeroDemo() {
  const [added, setAdded] = React.useState(false);
  // Bumped on every add so highlighted rows re-mount and replay their entrance.
  const [cycle, setCycle] = React.useState(0);

  React.useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setAdded(true);
      return;
    }

    let timer: ReturnType<typeof setTimeout>;
    const add = () => {
      setAdded(true);
      setCycle((c) => c + 1);
      timer = setTimeout(remove, HOLD_ADDED_MS);
    };
    const remove = () => {
      setAdded(false);
      timer = setTimeout(add, HOLD_EMPTY_MS);
    };

    timer = setTimeout(add, FIRST_ADD_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <figure className="relative mx-auto w-full max-w-xl lg:max-w-none">
      <figcaption className="sr-only">
        Example: adding BBQ chicken bowls to Friday puts their ingredients on the
        grocery list and combines amounts with what the week already needs.
      </figcaption>

      {/* Soft brand glow so the demo lifts off the page */}
      <div aria-hidden className="absolute -inset-6 rounded-full bg-primary/10 blur-3xl" />

      {/* A big plate of food behind the cards, so the first screen looks like dinner */}
      <div
        aria-hidden
        className="absolute inset-y-0 right-0 hidden w-3/4 overflow-hidden rounded-3xl bg-elevated shadow-elevated sm:block"
      >
        <Image
          src={SHRIMP_PASTA.image}
          alt=""
          fill
          priority
          sizes="(max-width: 1024px) 75vw, 560px"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-background/40 to-transparent" />
      </div>

      <div aria-hidden className="relative grid grid-cols-1 gap-4 sm:grid-cols-5 sm:items-start sm:py-10 sm:pr-6">
        <PlannerCard added={added} cycle={cycle} />
        <ListCard added={added} cycle={cycle} />
      </div>
    </figure>
  );
}

function PlannerCard({ added, cycle }: { added: boolean; cycle: number }) {
  return (
    <Card className="gap-0 p-0 shadow-floating sm:col-span-3">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <CalendarDays className="size-4 text-primary" strokeWidth={1.5} />
          This week
        </span>
        <span className="text-xs text-muted-foreground">{added ? 5 : 4} dinners planned</span>
      </div>
      <ul className="flex flex-col gap-2 p-3">
        {PLANNED_WEEK.map((night) => (
          <li key={night.day}>
            <NightRow night={night} />
          </li>
        ))}
        <li>
          {added ? (
            <NightRow key={cycle} night={FRIDAY_NIGHT} fresh />
          ) : (
            <div className="flex h-14 items-center gap-3 rounded-lg border border-dashed border-border-strong px-2 text-muted-foreground animate-fade-in">
              <span className="w-8 shrink-0 text-xs font-semibold">Fri</span>
              <span className="flex items-center gap-1.5 text-sm">
                <Plus className="size-4" strokeWidth={1.5} />
                Add a meal
              </span>
            </div>
          )}
        </li>
      </ul>
    </Card>
  );
}

function NightRow({ night, fresh = false }: { night: PlannedNight; fresh?: boolean }) {
  return (
    <div
      className={cn(
        "flex h-14 items-center gap-3 rounded-lg border px-2",
        fresh
          ? "border-primary bg-primary-surface animate-scale-in"
          : "border-border bg-background"
      )}
    >
      <span className="w-8 shrink-0 text-xs font-semibold text-muted-foreground">{night.day}</span>
      <span className="relative flex shrink-0">
        <Thumb src={night.main.image} />
        {night.side && <Thumb src={night.side.image} className="-ml-3 ring-2 ring-card" />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">{night.main.name}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {night.side ? `with ${night.side.name}` : night.main.time}
        </span>
      </span>
      {fresh && (
        <Badge variant="default" className="mr-1 shrink-0">
          Added
        </Badge>
      )}
    </div>
  );
}

function Thumb({ src, className }: { src: string; className?: string }) {
  return (
    <span className={cn("relative size-10 overflow-hidden rounded-md bg-elevated", className)}>
      <Image src={src} alt="" fill sizes="40px" className="object-cover" />
    </span>
  );
}

function ListCard({ added, cycle }: { added: boolean; cycle: number }) {
  const rows = GROCERY_LIST.filter((item) => added || item.before);

  return (
    <Card className="relative gap-0 overflow-hidden p-0 shadow-floating sm:col-span-2 sm:mt-12">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <ShoppingCart className="size-4 text-primary" strokeWidth={1.5} />
          Grocery list
        </span>
        <span key={added ? `a${cycle}` : "b"} className="text-xs text-muted-foreground animate-fade-in">
          {added ? LIST_TOTAL_AFTER : LIST_TOTAL_BEFORE} items
        </span>
      </div>
      <ul className="flex h-64 flex-col gap-1 p-3 sm:h-80">
        {rows.map((item) => {
          // Re-key changed rows each cycle so their highlight replays.
          const changes = added && Boolean(item.after);
          return (
            <GroceryRow key={changes ? `${item.name}-${cycle}` : item.name} item={item} added={added} />
          );
        })}
      </ul>
      {/* Fade the overflow so the list reads as "and more" */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-card to-transparent" />
    </Card>
  );
}

function GroceryRow({ item, added }: { item: ListItem; added: boolean }) {
  const isNew = added && !item.before;
  const isCombined = added && Boolean(item.before && item.after);
  const highlight = isNew || isCombined;
  const qty = added ? item.after ?? item.before : item.before;
  const count = added ? item.recipes[1] : item.recipes[0];

  return (
    <li
      className={cn(
        "flex shrink-0 items-center justify-between gap-2 rounded-md px-2 py-1.5 transition-colors duration-500",
        highlight ? "bg-primary-surface" : "bg-transparent",
        isNew && "animate-slide-down"
      )}
    >
      <span className="min-w-0">
        <span className="block truncate text-sm text-foreground">{item.name}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {count === 1 ? "1 recipe" : `${count} recipes`}
        </span>
      </span>
      <span
        className={cn(
          "shrink-0 text-sm tabular-nums",
          highlight ? "font-semibold text-primary-on-surface" : "text-foreground-subtle"
        )}
      >
        {qty}
      </span>
    </li>
  );
}
