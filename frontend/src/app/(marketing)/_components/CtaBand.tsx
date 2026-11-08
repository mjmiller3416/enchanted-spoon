import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PRO_ANNUAL_PRICE_LABEL, PRO_MONTHLY_PRICE_LABEL, PRO_TRIAL_DAYS } from "@/lib/pro-plans";
import { cn } from "@/lib/utils";
import { APPLE_COBBLER, BBQ_CHICKEN_BOWL, RIBEYE_STEAK, SHRIMP_PASTA, STUFFED_CHICKEN } from "./examples";

const PLATES = [STUFFED_CHICKEN, RIBEYE_STEAK, SHRIMP_PASTA, BBQ_CHICKEN_BOWL, APPLE_COBBLER];

export function CtaBand() {
  return (
    <section aria-labelledby="cta-heading" className="overflow-x-clip border-t border-border bg-background-subtle">
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-16 text-center lg:px-6 lg:py-24">
        <div aria-hidden className="flex items-center">
          {PLATES.map((plate, index) => (
            <span
              key={plate.name}
              className={cn(
                "relative size-16 overflow-hidden rounded-full bg-elevated shadow-raised ring-4 ring-background-subtle sm:size-20",
                index > 0 && "-ml-4",
                index === 2 && "z-10 size-20 sm:size-24"
              )}
            >
              <Image src={plate.image} alt="" fill sizes="96px" className="object-cover" />
            </span>
          ))}
        </div>
        <h2 id="cta-heading" className="font-display text-4xl leading-tight text-foreground sm:text-5xl">
          Ready for an easier week of dinners?
        </h2>
        <p className="max-w-xl text-lg leading-relaxed text-foreground-subtle">
          Start with one recipe you already love. You&apos;ll have a plan and a
          grocery list in a few minutes.
        </p>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href="/sign-up">Start for free</Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
            <Link href="/pricing">See pricing</Link>
          </Button>
        </div>
        <p className="max-w-lg text-sm leading-relaxed text-muted-foreground">
          Recipes, meal planning, grocery lists, and household sharing are free.
          Pro adds link import, recipe drafts, and more for {PRO_MONTHLY_PRICE_LABEL}/month
          or {PRO_ANNUAL_PRICE_LABEL}/year (plus tax) after a {PRO_TRIAL_DAYS}-day free trial.
        </p>
      </div>
    </section>
  );
}
