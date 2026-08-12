import { Wand2, Sparkles, Apple, Flame, type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Reveal } from "./Reveal";
import { PlannerVignette, ShoppingVignette } from "./demo/FeatureVignettes";

interface Highlight {
  vignette: React.ReactNode;
  title: string;
  body: string;
}

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
}

// Live component slices instead of screenshots — crisp, theme-aware, and
// identical to what users see after signing up.
const HIGHLIGHTS: Highlight[] = [
  {
    vignette: <PlannerVignette />,
    title: "Weekly meal planner",
    body: "Line up the week's dinners in one board. Mains, sides, and servings — rearrange with a drag.",
  },
  {
    vignette: <ShoppingVignette />,
    title: "Auto-built shopping list",
    body: "Every planned meal feeds one list — quantities combined, sorted by aisle, checked off as you shop.",
  },
];

const FEATURES: Feature[] = [
  {
    icon: Wand2,
    title: "AI recipe generation & import",
    body: "Paste a URL or describe a dish — get a complete, editable recipe in seconds.",
  },
  {
    icon: Sparkles,
    title: "Genie assistant",
    body: "Ask for anything — “something cozy, no oven, 30 minutes” — and the Genie drafts the recipe.",
  },
  {
    icon: Apple,
    title: "Nutrition facts",
    body: "Calories and macros for every recipe, estimated automatically.",
  },
  {
    icon: Flame,
    title: "Cooking streaks",
    body: "Track the nights you actually cook and keep the streak alive.",
  },
];

export function FeatureGrid() {
  return (
    <section aria-labelledby="features-heading" className="border-t border-border bg-background-subtle">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-4 py-20 lg:px-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <h2
            id="features-heading"
            className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl"
          >
            Everything between recipe and dinner table
          </h2>
          <p className="max-w-xl text-muted-foreground">
            One app for the whole loop — saving, planning, shopping, and cooking.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {HIGHLIGHTS.map((highlight, index) => (
            <Reveal key={highlight.title} delay={index * 150} className="h-full">
              <Card className="h-full gap-0 overflow-hidden pt-0 pb-0">
                <div
                  aria-hidden
                  className="flex flex-1 items-center border-b border-border bg-background-subtle p-6"
                >
                  <div className="w-full">{highlight.vignette}</div>
                </div>
                <CardContent className="flex flex-col gap-2">
                  <h3 className="text-lg font-semibold text-foreground">{highlight.title}</h3>
                  <p className="text-sm text-muted-foreground">{highlight.body}</p>
                </CardContent>
              </Card>
            </Reveal>
          ))}
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature, index) => (
            <Reveal key={feature.title} delay={index * 100} className="h-full">
              <Card className="h-full transition-transform hover:-translate-y-1">
                <CardContent className="flex flex-col gap-3">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-primary-surface text-primary">
                    <feature.icon className="size-5" strokeWidth={1.5} />
                  </div>
                  <h3 className="font-semibold text-foreground">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.body}</p>
                </CardContent>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
