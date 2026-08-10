import { Reveal } from "./Reveal";
import { PlanVignette, SaveVignette, ShopVignette } from "./demo/StepVignettes";

interface Step {
  vignette: React.ReactNode;
  title: string;
  body: string;
}

// The core loop, told through one recipe: the shrimp pasta from the hero gets
// saved, lands on Tuesday, and its ingredients show up on the list.
const STEPS: Step[] = [
  {
    vignette: <SaveVignette />,
    title: "Save recipes",
    body: "Type them in, import from any URL, or let the Genie generate one for you.",
  },
  {
    vignette: <PlanVignette />,
    title: "Plan your week",
    body: "Drag meals into your weekly menu — mains, sides, and servings included.",
  },
  {
    vignette: <ShopVignette />,
    title: "Shop once",
    body: "Your shopping list builds itself from the plan, aggregated and sorted by aisle.",
  },
];

export function HowItWorks() {
  return (
    <section aria-labelledby="how-it-works-heading" className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-4 py-20 lg:px-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <h2
            id="how-it-works-heading"
            className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl"
          >
            How it works
          </h2>
          <p className="max-w-xl text-muted-foreground">
            Three steps from &ldquo;what&apos;s for dinner?&rdquo; to a finished grocery
            run — watch one recipe make the trip.
          </p>
        </div>

        <ol className="grid gap-10 md:grid-cols-3 md:gap-6 lg:gap-10">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <Reveal delay={index * 150} className="flex h-full flex-col items-center gap-5 text-center">
                <div
                  aria-hidden
                  className="flex h-80 w-full items-center justify-center rounded-xl border border-border bg-background-subtle p-4"
                >
                  {step.vignette}
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="flex items-center gap-3">
                    <span className="flex size-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                      {index + 1}
                    </span>
                    <h3 className="text-lg font-semibold text-foreground">{step.title}</h3>
                  </div>
                  <p className="max-w-xs text-sm text-muted-foreground">{step.body}</p>
                </div>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
