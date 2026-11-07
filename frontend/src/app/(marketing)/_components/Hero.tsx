import Link from "next/link";
import { Button } from "@/components/ui/button";
import { WeeknightPlate } from "./WeeknightPlate";

const FIRST_USE = [
  {
    step: "1",
    title: "Create a free account",
    body: "Sign up with email. No card for the free plan.",
  },
  {
    step: "2",
    title: "Save one dinner",
    body: "Write the name, ingredients, and steps for a dish you already cook.",
  },
  {
    step: "3",
    title: "Plan it, then shop",
    body: "Put that recipe on a night. Its ingredients land on the shopping list.",
  },
];

export function Hero() {
  return (
    <section aria-labelledby="hero-heading" className="overflow-x-clip">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-4 py-12 sm:py-16 lg:px-6 lg:py-20">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="flex flex-col gap-6">
            <p className="text-sm font-medium tracking-wide text-primary">Weeknight cooking</p>
            <h1
              id="hero-heading"
              className="font-display text-4xl leading-tight text-foreground sm:text-5xl lg:text-6xl"
            >
              A recipe box for the week you&apos;re actually cooking.
            </h1>
            <p className="max-w-xl text-lg leading-relaxed text-foreground-subtle">
              Save the dishes you make, give each night a meal, and take one grocery list to the store.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button asChild size="lg" className="w-full sm:w-auto">
                <Link href="/sign-up">Create a free account</Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
                <Link href="/sign-in">Sign in</Link>
              </Button>
            </div>
          </div>
          <WeeknightPlate />
        </div>
        <ol className="grid gap-3 md:grid-cols-3">
          {FIRST_USE.map((item) => (
            <li key={item.step} className="flex gap-3 rounded-lg border border-border bg-card p-4 shadow-sm">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                {item.step}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-foreground">{item.title}</span>
                <span className="mt-1 block text-sm leading-relaxed text-muted-foreground">{item.body}</span>
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
