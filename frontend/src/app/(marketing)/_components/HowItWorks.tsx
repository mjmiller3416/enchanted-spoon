import Image from "next/image";
import { CheckCircle2, Circle, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AVOCADO_CORN_SALAD, FISH_SANDWICHES, RIBEYE_STEAK, SHRIMP_PASTA } from "./examples";
import { Reveal } from "./Reveal";

const STEPS = [
  {
    title: "Save your recipes",
    body: "Type in the dishes you already make, or paste a link from a recipe site and skip the life story. Edit anything, any time.",
    visual: <RecipeVisual />,
  },
  {
    title: "Plan your week",
    body: "Pick a main for any night and add up to three sides. Plans change? Drag the meal to another day.",
    visual: <PlanVisual />,
  },
  {
    title: "Shop with one list",
    body: "Every planned meal adds its ingredients to one list, with amounts combined and items sorted by category.",
    visual: <ShopVisual />,
  },
];

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      aria-labelledby="how-it-works-heading"
      className="scroll-mt-[calc(4rem+env(safe-area-inset-top,0px))] border-t border-border bg-background-subtle"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-4 py-16 lg:px-6 lg:py-24">
        <div className="flex max-w-2xl flex-col gap-3">
          <p className="text-sm font-semibold text-primary">How it works</p>
          <h2 id="how-it-works-heading" className="font-display text-3xl leading-tight text-foreground sm:text-5xl">
            From recipe to grocery run in three steps
          </h2>
        </div>

        <ol className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <Reveal delay={index * 120} className="h-full">
                <Card className="h-full gap-0 overflow-hidden p-0">
                  <div aria-hidden className="flex h-64 flex-col justify-center border-b border-border bg-background p-5">
                    {step.visual}
                  </div>
                  <CardContent className="flex flex-col gap-2 py-6">
                    <h3 className="flex items-center gap-3 text-lg font-semibold text-foreground">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                        {index + 1}
                      </span>
                      {step.title}
                    </h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
                  </CardContent>
                </Card>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function RecipeVisual() {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 rounded-full border border-border bg-card py-1.5 pr-1.5 pl-3 shadow-sm">
        <Link2 className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} />
        <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          myfavoritefoodblog.com/shrimp-pasta
        </span>
        <Badge variant="default" className="shrink-0 rounded-full">
          Import
        </Badge>
      </div>
      <div className="flex gap-3 rounded-xl border border-border bg-card p-3 shadow-raised">
        <span className="relative size-20 shrink-0 overflow-hidden rounded-lg bg-elevated">
          <Image src={SHRIMP_PASTA.image} alt="" fill sizes="80px" className="object-cover" />
        </span>
        <div className="flex min-w-0 flex-col gap-1">
          <p className="truncate font-display text-base text-foreground">{SHRIMP_PASTA.name}</p>
          <ul className="flex flex-col text-xs text-muted-foreground">
            <li>1 lb shrimp</li>
            <li>12 oz spaghetti</li>
            <li>4 cloves garlic, 3 tbsp butter</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

const PLAN_DAYS = [
  { day: "Mon", recipe: RIBEYE_STEAK },
  { day: "Tue", recipe: SHRIMP_PASTA, side: AVOCADO_CORN_SALAD, active: true },
  { day: "Wed", recipe: FISH_SANDWICHES },
];

function PlanVisual() {
  return (
    <div className="flex flex-col gap-2">
      {PLAN_DAYS.map(({ day, recipe, side, active }) => (
        <div
          key={day}
          className={cn(
            "flex items-center gap-3 rounded-lg border bg-card p-2",
            active ? "translate-x-2 -rotate-1 border-primary shadow-elevated" : "border-border"
          )}
        >
          <span className="w-8 shrink-0 text-xs font-semibold text-muted-foreground">{day}</span>
          <span className="relative size-10 shrink-0 overflow-hidden rounded-md bg-elevated">
            <Image src={recipe.image} alt="" fill sizes="40px" className="object-cover" />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium text-foreground">{recipe.name}</span>
            <span className="block truncate text-xs text-muted-foreground">
              {side ? `+ ${side.name}` : recipe.time}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}

const SHOP_GROUPS = [
  {
    label: "Produce",
    items: [
      { name: "Avocados", qty: "2", done: true },
      { name: "Lemons", qty: "3", done: true },
      { name: "Parsley", qty: "1 bunch", done: false },
    ],
  },
  {
    label: "Seafood",
    items: [
      { name: "Shrimp", qty: "1 lb", done: false },
      { name: "Cod fillets", qty: "1 lb", done: false },
    ],
  },
];

function ShopVisual() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3 shadow-raised">
      {SHOP_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-1">
          <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{group.label}</p>
          {group.items.map((item) => (
            <div key={item.name} className="flex items-center gap-2 text-sm">
              {item.done ? (
                <CheckCircle2 className="size-4 shrink-0 text-primary" strokeWidth={1.5} />
              ) : (
                <Circle className="size-4 shrink-0 text-border-strong" strokeWidth={1.5} />
              )}
              <span className={cn("flex-1 truncate", item.done ? "text-muted-foreground line-through" : "text-foreground")}>
                {item.name}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{item.qty}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
