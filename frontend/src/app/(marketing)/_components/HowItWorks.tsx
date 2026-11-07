import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { AVOCADO_CORN_SALAD, SHRIMP_PASTA, TUESDAY_INGREDIENTS } from "./examples";
import { Reveal } from "./Reveal";

const STEPS = [
  {
    title: "Save the recipe",
    body: "Type the dish the way you cook it, then edit it whenever it changes. A recipe that already lives on a web page can be copied in from its link — that import is part of the 7-day trial and Pro.",
  },
  {
    title: "Give it a night",
    body: "Drop the main on the weekly menu and add up to three sides. Servings stay with the meal, so Tuesday is for four, not a guess.",
  },
  {
    title: "Shop once",
    body: "Each meal can add all of its ingredients, produce only, or nothing. Quantities for the same item combine and group the way you walk the store.",
  },
];

export function HowItWorks() {
  return (
    <section aria-labelledby="how-it-works-heading" className="border-t border-border bg-background-subtle">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-4 py-16 lg:px-6 lg:py-20">
        <div className="flex max-w-2xl flex-col gap-3">
          <h2 id="how-it-works-heading" className="font-display text-3xl leading-tight text-foreground sm:text-4xl">
            One pasta, from the recipe box to the store
          </h2>
          <p className="text-muted-foreground">
            An example, not someone else&apos;s account. Garlic butter shrimp pasta is saved, set on Tuesday with a side, and its ingredients show up on the list.
          </p>
        </div>

        <ol className="grid gap-6 lg:grid-cols-3">
          <li>
            <Reveal className="h-full">
              <Card className="h-full gap-0 overflow-hidden pt-0 pb-0">
                <RecipeSlip />
                <CardContent className="flex flex-col gap-2">
                  <StepTitle index={1} title={STEPS[0].title} />
                  <p className="text-sm leading-relaxed text-muted-foreground">{STEPS[0].body}</p>
                </CardContent>
              </Card>
            </Reveal>
          </li>
          <li>
            <Reveal delay={120} className="h-full">
              <Card className="h-full gap-0 overflow-hidden pt-0 pb-0">
                <PlanSlip />
                <CardContent className="flex flex-col gap-2">
                  <StepTitle index={2} title={STEPS[1].title} />
                  <p className="text-sm leading-relaxed text-muted-foreground">{STEPS[1].body}</p>
                </CardContent>
              </Card>
            </Reveal>
          </li>
          <li>
            <Reveal delay={240} className="h-full">
              <Card className="h-full gap-0 overflow-hidden pt-0 pb-0">
                <ShopSlip />
                <CardContent className="flex flex-col gap-2">
                  <StepTitle index={3} title={STEPS[2].title} />
                  <p className="text-sm leading-relaxed text-muted-foreground">{STEPS[2].body}</p>
                </CardContent>
              </Card>
            </Reveal>
          </li>
        </ol>
      </div>
    </section>
  );
}

function StepTitle({ index, title }: { index: number; title: string }) {
  return (
    <h3 className="flex items-center gap-3 text-lg font-semibold text-foreground">
      <span className="flex size-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
        {index}
      </span>
      {title}
    </h3>
  );
}

function RecipeSlip() {
  return (
    <div className="flex flex-col gap-3 border-b border-border bg-background p-4" aria-hidden>
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Example recipe</p>
      <p className="font-display text-xl text-foreground">{SHRIMP_PASTA.name}</p>
      <ul className="flex flex-col gap-1 text-sm text-foreground-subtle">
        <li>Shrimp, 1 lb</li>
        <li>Spaghetti, 12 oz</li>
        <li>Garlic, butter, parsley, lemon</li>
      </ul>
      <p className="truncate rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
        example.com/garlic-butter-shrimp-pasta
      </p>
    </div>
  );
}

function PlanSlip() {
  return (
    <div className="flex flex-col gap-3 border-b border-border bg-background p-4" aria-hidden>
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Example menu</p>
      <div className="flex items-center gap-3 rounded-lg border border-primary bg-card p-2">
        <span className="relative size-12 shrink-0 overflow-hidden rounded-md bg-elevated">
          <Image src={SHRIMP_PASTA.image} alt="" fill sizes="48px" className="object-cover" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium text-foreground">Tue · {SHRIMP_PASTA.name}</span>
          <span className="block text-xs text-muted-foreground">{SHRIMP_PASTA.servings} servings · {SHRIMP_PASTA.time}</span>
        </span>
      </div>
      <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-2">
        <span className="relative size-12 shrink-0 overflow-hidden rounded-md bg-elevated">
          <Image src={AVOCADO_CORN_SALAD.image} alt="" fill sizes="48px" className="object-cover" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium text-foreground">Side · {AVOCADO_CORN_SALAD.name}</span>
          <span className="block text-xs text-muted-foreground">{AVOCADO_CORN_SALAD.time}</span>
        </span>
      </div>
    </div>
  );
}

function ShopSlip() {
  return (
    <div className="flex flex-col gap-2 border-b border-border bg-background p-4" aria-hidden>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Example list</p>
        <Badge variant="outline">All ingredients</Badge>
      </div>
      {TUESDAY_INGREDIENTS.slice(0, 4).map((item) => (
        <div key={item.name} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2">
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium text-foreground">{item.name}</span>
            <span className="block truncate text-xs text-muted-foreground">{item.source}</span>
          </span>
          <span className="shrink-0 text-sm text-foreground-subtle">{item.qty}</span>
        </div>
      ))}
    </div>
  );
}
