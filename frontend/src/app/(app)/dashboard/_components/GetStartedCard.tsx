"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  CalendarDays,
  Check,
  CircleCheck,
  Link as LinkIcon,
  Plus,
  ShoppingCart,
  Sparkles,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRecipeWizardDialog } from "@/lib/providers/RecipeWizardProvider";
import { useAssistantDialog } from "@/lib/providers/AssistantProvider";
import { appConfig } from "@/lib/config";

interface GetStartedCardProps {
  recipesDone: boolean;
  planDone: boolean;
}

/**
 * GetStartedCard — guided first-run setup shown on Home when the user has
 * no recipes and no planner entries. Replaces the four-isolated-zeros
 * experience with one three-step path to a planned week.
 */
export function GetStartedCard({ recipesDone, planDone }: GetStartedCardProps) {
  const router = useRouter();
  const { openWizard } = useRecipeWizardDialog();
  const { openAssistant } = useAssistantDialog();

  return (
    <Card className="gap-0 p-6 shadow-raised md:p-8">
      <h3 className="text-xl font-semibold text-foreground">
        Welcome to {appConfig.appName} ✨
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Three steps to your first planned week.
      </p>

      <ol className="mt-6 flex flex-col gap-6">
        <SetupStep number={1} done={recipesDone} title="Add your first recipe">
          <div className="flex flex-wrap gap-2">
            <Button onClick={openWizard}>
              <Plus className="size-4" strokeWidth={1.5} />
              Add a recipe
            </Button>
            <Button variant="outline" onClick={openWizard}>
              <LinkIcon className="size-4" strokeWidth={1.5} />
              Import from URL
            </Button>
            <Button variant="outline" onClick={openAssistant}>
              <Sparkles className="size-4" strokeWidth={1.5} />
              Ask the Genie
            </Button>
          </div>
        </SetupStep>

        <SetupStep number={2} done={planDone} title="Plan your first meal">
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              onClick={() => router.push("/meal-planner?addMeal=1")}
              disabled={!recipesDone}
            >
              <CalendarDays className="size-4" strokeWidth={1.5} />
              Plan a meal
            </Button>
            {!recipesDone && (
              <span className="text-xs text-muted-foreground">
                Unlocks after step 1
              </span>
            )}
          </div>
        </SetupStep>

        <SetupStep number={3} done={false} title="Shop from your auto-list">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <ShoppingCart className="size-4" strokeWidth={1.5} />
            Your shopping list builds itself from the plan.
          </p>
        </SetupStep>
      </ol>
    </Card>
  );
}

interface SetupStepProps {
  number: number;
  done: boolean;
  title: string;
  children: ReactNode;
}

function SetupStep({ number, done, title, children }: SetupStepProps) {
  return (
    <li className="flex gap-4">
      <div
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold",
          done
            ? "bg-secondary text-secondary-foreground"
            : "border border-border text-muted-foreground"
        )}
      >
        {done ? <Check className="size-4" strokeWidth={2.5} /> : number}
      </div>
      <div className="flex min-w-0 flex-col gap-2 pt-1">
        <p
          className={cn(
            "text-sm font-medium",
            done ? "text-muted-foreground line-through" : "text-foreground"
          )}
        >
          {title}
        </p>
        {children}
      </div>
    </li>
  );
}

/**
 * GetStartedBanner — slim residual progress banner shown once recipes exist
 * but no meal has been planned yet. Disappears forever after the first
 * planner entry (persisted via useGetStartedComplete).
 */
export function GetStartedBanner() {
  const router = useRouter();

  return (
    <Card className="flex-row items-center gap-3 p-4 shadow-raised">
      <CircleCheck className="size-5 shrink-0 text-secondary" strokeWidth={1.5} />
      <p className="min-w-0 flex-1 text-sm text-foreground">
        <span className="font-medium">Recipe added!</span>{" "}
        <span className="text-muted-foreground">
          Next: plan your first meal — your shopping list will build itself.
        </span>
      </p>
      <Button
        size="sm"
        onClick={() => router.push("/meal-planner?addMeal=1")}
        className="shrink-0"
      >
        Plan a meal
      </Button>
    </Card>
  );
}
