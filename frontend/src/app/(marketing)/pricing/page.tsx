import type { Metadata } from "next";
import Link from "next/link";
import { Check, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { appConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${appConfig.appName} is free for recipes, meal planning, and shopping lists. Go Pro for larger AI allowances — recipe import, generation, food photography, and the assistant.`,
};

const FREE_FEATURES = [
  "Recipes, collections, and favorites",
  "Meal planning and your grocery list",
  "No monthly free AI allowance",
];

const PRO_FEATURES = [
  "7-day trial, card required",
  "Import recipes from a URL",
  "Generate complete recipes from a prompt",
  "On-demand AI photos (banners are cropped from the square photo)",
  "Genie assistant",
  "Monthly: 20 photos, 200 AI suggestions, 300 Genie messages, 50 imports",
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
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Start free. <span className="text-primary">Go Pro for the magic.</span>
        </h1>
        <p className="text-lg text-muted-foreground">
          Existing accounts created before release keep a free AI taste until
          Mar 31, 2027. After that they become read-only. New accounts keep
          recipes and the grocery list free. AI starts with a 7-day trial,
          then Pro at $6.99/mo or $49.99/yr plus applicable tax.
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
              Recipes, meal planning, and your grocery list. AI needs a trial.
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
              <Badge>
                <Sparkles className="mr-1 h-3 w-3" strokeWidth={1.5} />
                More AI
              </Badge>
            </div>
            <p className="flex items-baseline gap-1">
              <span className="text-4xl font-bold tracking-tight text-foreground">$6.99</span>
              <span className="text-sm text-muted-foreground">/mo plus applicable tax</span>
            </p>
            <p className="text-sm text-muted-foreground">
              or $49.99/yr plus applicable tax. Founding codes FOUNDER30 and FOUNDER30Y are web checkout only.
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

      <p className="text-sm text-muted-foreground">
        Already using {appConfig.appName}? Upgrade anytime from{" "}
        <span className="font-medium text-foreground">Settings → Plan &amp; Billing</span>.
        Cancel whenever. Prices are tax-exclusive. A photo is one square image;
        banners are cropped from it. Allowances reset each calendar month for
        paid plans and cover the whole 7-day trial.
      </p>
    </section>
  );
}
