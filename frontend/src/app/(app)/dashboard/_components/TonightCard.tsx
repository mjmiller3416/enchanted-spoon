"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CalendarDays,
  Check,
  Clock,
  Dices,
  ExternalLink,
  Loader2,
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RecipeBannerImage } from "@/components/recipe/RecipeBannerImage";
import { formatTime } from "@/lib/quantityUtils";
import { useMeal, useMarkComplete, useRecipeCards } from "@/hooks/api";
import type { PlannerEntryResponseDTO } from "@/types/planner";

interface TonightCardProps {
  /** Next uncompleted planner entry (lowest position), or null when none */
  entry: PlannerEntryResponseDTO | null;
  isLoading?: boolean;
}

/**
 * TonightCard — the Home hero. Shows the next uncompleted meal from the
 * planner with Mark cooked / View recipe actions. When nothing is planned,
 * swaps to a "Plan your week" prompt.
 */
export function TonightCard({ entry, isLoading = false }: TonightCardProps) {
  // Hydrated meal (side recipe names live here, not on the planner entry)
  const { data: meal } = useMeal(entry?.meal_id ?? null);
  const markComplete = useMarkComplete();

  if (isLoading) {
    return <TonightCardSkeleton />;
  }

  if (!entry) {
    return <PlanWeekCard />;
  }

  const recipe = entry.main_recipe;
  const mealName = entry.meal_name || recipe?.recipe_name || "Unnamed Meal";
  const showMainName =
    recipe?.recipe_name && recipe.recipe_name !== mealName;
  const sideNames =
    meal?.side_recipes?.map((r) => r.recipe_name).filter(Boolean) ?? [];
  const totalTime = meal?.total_cook_time ?? recipe?.total_time ?? null;
  const servings = recipe?.servings ?? null;

  return (
    <Card className="h-full gap-0 overflow-hidden p-0 shadow-raised">
      <div className="grid h-full md:min-h-64 md:grid-cols-[3fr_2fr]">
        {/* Hero image */}
        <div className="relative">
          <RecipeBannerImage
            bannerSrc={recipe?.banner_image_path}
            fallbackSrc={recipe?.reference_image_path}
            alt={mealName}
            aspectRatio="16/9"
            className="h-full md:aspect-auto"
          />
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center rounded-full bg-background/70 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-foreground backdrop-blur-md">
              Up next
            </span>
          </div>
        </div>

        {/* Details */}
        <div className="flex flex-col gap-2 p-5">
          <h3 className="text-2xl font-semibold leading-tight text-foreground">
            {mealName}
          </h3>

          {(showMainName || sideNames.length > 0) && (
            <p className="text-sm text-muted-foreground">
              {showMainName && recipe.recipe_name}
              {showMainName && sideNames.length > 0 && " · "}
              {sideNames.length > 0 && `with ${sideNames.join(", ")}`}
            </p>
          )}

          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {totalTime != null && (
              <span className="flex items-center gap-1">
                <Clock className="size-4" strokeWidth={1.5} />
                {formatTime(totalTime)}
              </span>
            )}
            {totalTime != null && servings != null && (
              <span className="h-3 w-px bg-border" />
            )}
            {servings != null && (
              <span className="flex items-center gap-1">
                <Users className="size-4" strokeWidth={1.5} />
                {servings} servings
              </span>
            )}
          </div>

          <div className="flex-1" />

          <div className="flex flex-col gap-2 pt-2 sm:flex-row">
            <Button
              onClick={() => markComplete.mutate(entry.id)}
              disabled={markComplete.isPending}
              className="flex-1"
            >
              {markComplete.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Check className="size-4" strokeWidth={1.5} />
              )}
              Mark cooked
            </Button>
            {entry.main_recipe_id && (
              <Button variant="outline" asChild className="flex-1">
                <Link href={`/recipes/${entry.main_recipe_id}`}>
                  <ExternalLink className="size-4" strokeWidth={1.5} />
                  View recipe
                </Link>
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

/** Prompt shown when recipes exist but nothing is planned. */
function PlanWeekCard() {
  const router = useRouter();
  // This card only renders when the user has recipes, so the list is never empty
  const { data: recipes = [] } = useRecipeCards();

  const handleSurpriseMe = () => {
    if (recipes.length === 0) return;
    const random = recipes[Math.floor(Math.random() * recipes.length)];
    router.push(`/recipes/${random.id}`);
  };

  return (
    <Card className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center shadow-raised md:min-h-64">
      <div className="rounded-full bg-primary/10 p-4">
        <CalendarDays className="size-8 text-primary" strokeWidth={1.5} />
      </div>
      <h3 className="text-xl font-semibold text-foreground">Plan your next meal</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Pick meals from your recipes and your shopping list builds itself.
      </p>
      <div className="mt-1 flex flex-col gap-2 sm:flex-row">
        <Button asChild>
          <Link href="/meal-planner">Open the planner</Link>
        </Button>
        <Button
          variant="outline"
          onClick={handleSurpriseMe}
          disabled={recipes.length === 0}
        >
          <Dices className="size-4" strokeWidth={1.5} />
          Surprise me
        </Button>
      </div>
    </Card>
  );
}

/** Loading skeleton matching the hero layout to prevent layout shift. */
function TonightCardSkeleton() {
  return (
    <Card className="h-full gap-0 overflow-hidden p-0 shadow-raised">
      <div className="grid h-full md:min-h-64 md:grid-cols-[3fr_2fr]">
        <Skeleton className="aspect-video w-full rounded-none md:aspect-auto md:h-full" />
        <div className="flex flex-col gap-3 p-5">
          <Skeleton className="h-7 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
          <div className="flex-1" />
          <div className="flex gap-2">
            <Skeleton className="h-10 flex-1" />
            <Skeleton className="h-10 flex-1" />
          </div>
        </div>
      </div>
    </Card>
  );
}
