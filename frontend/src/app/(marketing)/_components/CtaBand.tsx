import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Reveal } from "./Reveal";
import { RecipeCardFan } from "./demo/RecipeCardFan";

export function CtaBand() {
  return (
    <section aria-labelledby="cta-heading" className="overflow-x-clip border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-10 px-4 py-20 text-center lg:px-6">
        <Reveal>
          <RecipeCardFan />
        </Reveal>
        <div className="flex flex-col items-center gap-6">
          <h2
            id="cta-heading"
            className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl"
          >
            This week&apos;s meals, planned in minutes.
          </h2>
          <p className="max-w-xl text-muted-foreground">
            Free to start — save your first recipe and plan your first week
            tonight. Go{" "}
            <Link
              href="/pricing"
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              Pro
            </Link>{" "}
            when you want the AI doing the heavy lifting.
          </p>
          <Button asChild size="lg">
            <Link href="/sign-up">Get started free</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
