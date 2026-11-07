import Image from "next/image";
import { Card } from "@/components/ui/card";
import { EXAMPLE_WEEK } from "./examples";
import { Reveal } from "./Reveal";

export function ExampleWeek() {
  return (
    <section aria-labelledby="example-week-heading" className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-16 lg:px-6 lg:py-20">
        <div className="flex max-w-2xl flex-col gap-3">
          <h2 id="example-week-heading" className="font-display text-3xl leading-tight text-foreground sm:text-4xl">
            A week you can picture
          </h2>
          <p className="text-muted-foreground">
            Illustrative dinners you could save yourself. Sunday is left open on purpose — the menu does not have to be full to be useful.
          </p>
        </div>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {EXAMPLE_WEEK.map((night, index) => (
            <li key={night.day}>
              <Reveal delay={index * 60} className="h-full">
                <Card className="h-full gap-3 p-3">
                  <div className="flex items-baseline justify-between px-1">
                    <h3 className="text-sm font-semibold text-foreground">{night.day}</h3>
                    {night.note && <span className="text-xs text-muted-foreground">{night.note}</span>}
                  </div>
                  {night.recipes.length === 0 ? (
                    <p className="rounded-lg border border-dashed border-border-strong px-3 py-6 text-center text-sm text-muted-foreground">
                      Nothing planned
                    </p>
                  ) : (
                    <ul className="flex flex-col gap-2">
                      {night.recipes.map((recipe) => (
                        <li key={recipe.name} className="flex items-center gap-3">
                          <span className="relative size-14 shrink-0 overflow-hidden rounded-md bg-elevated">
                            <Image src={recipe.image} alt="" fill sizes="56px" className="object-cover" />
                          </span>
                          <span className="min-w-0">
                            <span className="block text-sm font-medium text-foreground">{recipe.name}</span>
                            <span className="block text-xs text-muted-foreground">
                              {recipe.mealType} · {recipe.time} · {recipe.servings} servings
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
