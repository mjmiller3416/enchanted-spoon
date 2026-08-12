import type { Metadata } from "next";
import Link from "next/link";
import { Check, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { appConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${appConfig.appName} is free for recipes, meal planning, and shopping lists. Go Pro for full AI power — recipe import, generation, food photography, and the assistant.`,
};

const FREE_FEATURES = [
  "Unlimited recipes, collections, and favorites",
  "Weekly meal planner with cooking streaks",
  "Shopping list that builds itself from your plan",
  "Nutrition tracking and unit conversions",
  "A monthly taste of every AI feature",
];

const PRO_FEATURES = [
  "Everything in Free",
  "Import recipes from any URL",
  "Generate complete recipes from a prompt",
  "AI food photography for your recipes",
  "Genie assistant — chat, ideas, and tips",
  "Generous monthly limits you'll rarely feel",
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
          Recipes, meal planning, and shopping lists are free forever. Pro
          unlocks the full genie — AI import, generation, photography, and the
          assistant.
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
              The full kitchen toolkit, with a taste of the AI.
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
                Full AI
              </Badge>
            </div>
            <p className="flex items-baseline gap-1">
              <span className="text-4xl font-bold tracking-tight text-foreground">$4.99</span>
              <span className="text-sm text-muted-foreground">/ month</span>
            </p>
            <p className="text-sm text-muted-foreground">
              For cooks who want the genie doing the heavy lifting.
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
        Cancel whenever — your recipes stay yours.
      </p>
    </section>
  );
}
