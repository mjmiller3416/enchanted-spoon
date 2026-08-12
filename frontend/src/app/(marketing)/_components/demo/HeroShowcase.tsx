"use client";

import * as React from "react";
import { Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DemoRecipeCard } from "./DemoRecipeCard";
import { HERO_WISHES } from "./data";

const TYPE_DELAY_MS = 34;
const CARD_HOLD_MS = 3600;

/**
 * The "genie moment": a wish gets typed into an assistant-style input and the
 * finished recipe card materializes beside it. Cycles through HERO_WISHES.
 * SSR renders the first wish complete (good LCP, works without JS); the cycle
 * starts after hydration and is skipped entirely under prefers-reduced-motion.
 */
export function HeroShowcase() {
  const [wishIndex, setWishIndex] = React.useState(0);
  const [charCount, setCharCount] = React.useState(HERO_WISHES[0].wish.length);
  const [cardVisible, setCardVisible] = React.useState(true);

  React.useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let cancelled = false;
    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    async function cycle() {
      await sleep(CARD_HOLD_MS);
      let index = 0;
      while (!cancelled) {
        index = (index + 1) % HERO_WISHES.length;
        setCardVisible(false);
        await sleep(400);
        if (cancelled) return;
        setWishIndex(index);
        setCharCount(0);
        const wish = HERO_WISHES[index].wish;
        for (let i = 1; i <= wish.length; i++) {
          if (cancelled) return;
          setCharCount(i);
          await sleep(TYPE_DELAY_MS + Math.random() * 30);
        }
        await sleep(500);
        if (cancelled) return;
        setCardVisible(true);
        await sleep(CARD_HOLD_MS);
      }
    }

    cycle();
    return () => {
      cancelled = true;
    };
  }, []);

  const currentWish = HERO_WISHES[wishIndex].wish;

  return (
    <div aria-hidden className="relative w-full max-w-4xl">
      {/* Soft diffuse brand glow behind the whole showcase */}
      <div className="absolute inset-x-8 -inset-y-8 rounded-full bg-primary/15 blur-3xl" />

      <div className="relative grid items-center gap-8 lg:grid-cols-2 lg:gap-12">
        {/* The wish */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-sm font-medium text-primary">
            <Sparkles className="size-4" strokeWidth={1.5} />
            Ask the Genie
          </div>
          <div className="flex min-h-20 items-center gap-3 rounded-xl border border-border bg-card p-4 text-left shadow-raised">
            <p className="flex-1 text-base text-foreground">
              {currentWish.slice(0, charCount)}
              <span className="animate-caret-blink ml-0.5 inline-block h-5 w-0.5 translate-y-1 bg-primary" />
            </p>
            <Button size="icon" aria-label="Send wish" tabIndex={-1} className="pointer-events-none shrink-0">
              <Send className="size-4" strokeWidth={1.5} />
            </Button>
          </div>
          <p className="text-left text-sm text-muted-foreground">
            …and the recipe appears — ready to edit, plan, and shop.
          </p>
        </div>

        {/* The grant. All cards stay mounted (stacked in one grid cell) so
            images preload before their turn in the cycle. */}
        <div className="mx-auto grid w-full max-w-sm">
          {HERO_WISHES.map((entry, index) => (
            <div
              key={entry.recipe.name}
              className={cn(
                "col-start-1 row-start-1 transition-all duration-500 ease-out",
                cardVisible && index === wishIndex
                  ? "scale-100 opacity-100"
                  : "pointer-events-none scale-95 opacity-0"
              )}
            >
              <DemoRecipeCard
                recipe={entry.recipe}
                badge="ai"
                isFavorite
                priority={index === 0}
                imageSizes="(max-width: 640px) 100vw, 384px"
                className="shadow-glow-primary"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
