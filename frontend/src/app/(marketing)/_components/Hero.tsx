import Link from "next/link";
import { ArrowDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HeroDemo } from "./HeroDemo";

const REASSURANCES = [
  "Free plan, no credit card",
  "Share with your household",
  "Works on your phone and computer",
];

export function Hero() {
  return (
    <section aria-labelledby="hero-heading" className="overflow-x-clip">
      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 pt-12 pb-16 sm:pt-16 lg:grid-cols-12 lg:gap-10 lg:px-6 lg:pt-20 lg:pb-24">
        <div className="flex min-w-0 flex-col gap-6 lg:col-span-5">
          <h1
            id="hero-heading"
            className="font-display text-5xl leading-none tracking-tight text-foreground sm:text-6xl lg:text-7xl"
          >
            This week&apos;s dinners, <em className="text-primary">sorted.</em>
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-foreground-subtle">
            Keep the recipes you love in one place, put them on the nights
            you&apos;ll cook them, and get a grocery list that builds itself.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button asChild size="lg" className="w-full sm:w-auto">
              <Link href="/sign-up">Start for free</Link>
            </Button>
            <Button asChild variant="ghost" size="lg" className="w-full sm:w-auto">
              <Link href="#how-it-works">
                See how it works
                <ArrowDown className="size-4" strokeWidth={1.5} aria-hidden />
              </Link>
            </Button>
          </div>
          <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
            {REASSURANCES.map((line) => (
              <li key={line} className="flex items-center gap-2">
                <Check className="size-4 shrink-0 text-primary" strokeWidth={1.5} aria-hidden />
                {line}
              </li>
            ))}
          </ul>
        </div>
        <div className="min-w-0 lg:col-span-7">
          <HeroDemo />
        </div>
      </div>
    </section>
  );
}
