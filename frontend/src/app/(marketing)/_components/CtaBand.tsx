import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PRO_ANNUAL_PRICE_LABEL, PRO_MONTHLY_PRICE_LABEL, PRO_TRIAL_DAYS } from "@/lib/pro-plans";

export function CtaBand() {
  return (
    <section aria-labelledby="cta-heading" className="border-t border-border">
      <div className="mx-auto flex max-w-3xl flex-col items-start gap-6 px-4 py-16 text-left lg:px-6 lg:py-20">
        <h2 id="cta-heading" className="font-display text-3xl leading-tight text-foreground sm:text-4xl">
          Save tonight&apos;s dinner before you forget it.
        </h2>
        <p className="text-lg leading-relaxed text-foreground-subtle">
          Create a free account, write down one recipe you already make, and put it on this week&apos;s menu. The shopping list is ready when you are.
        </p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Recipes, meal planning, and the shopping list stay free. Link import and other kitchen tools start with a {PRO_TRIAL_DAYS}-day trial, then Pro at {PRO_MONTHLY_PRICE_LABEL} a month or {PRO_ANNUAL_PRICE_LABEL} a year, plus tax.
        </p>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href="/sign-up">Create a free account</Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
            <Link href="/pricing">See pricing</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
