import type { Metadata } from "next";
import Link from "next/link";
import { Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { WebFoundingOffer } from "@/components/billing/WebFoundingOffer";
import { appConfig } from "@/lib/config";
import { PRO_ANNUAL_PRICE_LABEL, PRO_MONTHLY_PRICE_LABEL, PRO_TRIAL_DAYS } from "@/lib/pro-plans";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${appConfig.appName} is free for recipes, meal planning, and shopping lists. Pro is ${PRO_MONTHLY_PRICE_LABEL} a month or ${PRO_ANNUAL_PRICE_LABEL} a year and adds link import, recipe drafts, food photos, and the kitchen assistant.`,
};

const FREE_FEATURES = [
  "Save, edit, and organize recipes",
  "Meal planning and your shopping list",
  "No monthly allowance for link import, drafts, photos, or the assistant",
];

const PRO_FEATURES = [
  "7-day trial, card required",
  "Import a recipe from a link",
  "Draft a complete recipe from a short description",
  "Food photos on demand (banners are cropped from the square photo)",
  "Kitchen assistant",
  "Monthly: 20 photos, 50 suggestions, 100 assistant messages, 25 imports",
];

function FeatureList({ features }: { features: string[] }) {
  return (
    <ul className="space-y-3">
      {features.map((feature) => (
        <li key={feature} className="flex items-start gap-3 text-sm text-muted-foreground">
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" strokeWidth={1.5} />
          {feature}
        </li>
      ))}
    </ul>
  );
}

export default function PricingPage() {
  return (
    <section className="mx-auto flex max-w-4xl flex-col items-center gap-12 px-4 pt-16 pb-24 sm:pt-24 lg:px-6">
      <div className="flex max-w-2xl flex-col items-center gap-4 text-center">
        <h1 className="font-display text-4xl leading-tight text-foreground sm:text-5xl">
          Free for the weekly cook. <span className="text-primary">Pro when you want extra help.</span>
        </h1>
        <p className="text-lg text-muted-foreground">
          Accounts created before release keep a free allowance for link import,
          recipe drafts, photos, and the assistant until March 31, 2027. After
          that they become read-only. New accounts keep recipes, meal planning,
          and the shopping list free. Those extra tools start with a {PRO_TRIAL_DAYS}-day
          trial, then Pro at {PRO_MONTHLY_PRICE_LABEL} a month or {PRO_ANNUAL_PRICE_LABEL} a
          year, plus applicable tax.
        </p>
      </div>

      <div className="grid w-full gap-6 sm:grid-cols-2">
        <Card className="h-full">
          <CardHeader className="gap-2">
            <h2 className="text-lg font-semibold text-foreground">Free</h2>
            <p className="flex items-baseline gap-1">
              <span className="text-4xl font-bold tracking-tight text-foreground">$0</span>
              <span className="text-sm text-muted-foreground">forever</span>
            </p>
            <p className="text-sm text-muted-foreground">
              Recipes, meal planning, and your shopping list. Link import, drafts, photos, and the assistant need a trial.
            </p>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-6">
            <FeatureList features={FREE_FEATURES} />
            <Button asChild variant="outline" className="mt-auto w-full">
              <Link href="/sign-up">Get started free</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="h-full border-primary/50">
          <CardHeader className="gap-2">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Pro</h2>
              <Badge>7-day trial</Badge>
            </div>
            <p className="flex flex-col gap-1">
              <span className="flex items-baseline gap-1">
                <span className="text-4xl font-bold tracking-tight text-foreground">{PRO_MONTHLY_PRICE_LABEL}</span>
                <span className="text-sm text-muted-foreground">/ month plus applicable tax</span>
              </span>
              <span className="flex items-baseline gap-1">
                <span className="text-2xl font-semibold tracking-tight text-foreground">{PRO_ANNUAL_PRICE_LABEL}</span>
                <span className="text-sm text-muted-foreground">/ year plus applicable tax</span>
              </span>
            </p>
            <p className="text-sm text-muted-foreground">
              {PRO_TRIAL_DAYS}-day free trial, then the plan you choose. Founding codes FOUNDER30 and FOUNDER30Y are web checkout only.
            </p>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-6">
            <FeatureList features={PRO_FEATURES} />
            <Button asChild className="mt-auto w-full">
              <Link href="/sign-up">Start with Pro</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <WebFoundingOffer />

      <p className="text-sm text-muted-foreground">
        Already using {appConfig.appName}? Upgrade anytime from{" "}
        <span className="font-medium text-foreground">Settings → Plan &amp; Billing</span>.
        Cancel whenever — your recipes stay yours. Prices are tax-exclusive. In the iOS and Android apps, Pro is
        purchased through the App Store or Google Play at the same prices. Allowances reset each calendar month for
        paid plans and cover the whole 7-day trial.
      </p>
    </section>
  );
}
