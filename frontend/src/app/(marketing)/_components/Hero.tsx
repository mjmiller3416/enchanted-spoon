import Link from "next/link";
import { Button } from "@/components/ui/button";
import { HeroShowcase } from "./demo/HeroShowcase";

export function Hero() {
  return (
    <section className="overflow-x-clip">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-14 px-4 pt-16 pb-20 text-center sm:pt-24 lg:px-6">
        <div className="flex max-w-3xl flex-col items-center gap-6">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Save recipes. Plan the week.{" "}
            <span className="text-primary">The shopping list writes itself.</span>
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            Whiskful keeps your recipes, weekly menu, and grocery run in one
            place — with AI that imports recipes from any URL or dreams up new ones.
          </p>
          <div className="flex items-center gap-4">
            <Button asChild size="lg">
              <Link href="/sign-up">Get started free</Link>
            </Button>
            <Button asChild variant="ghost" size="lg">
              <Link href="/sign-in">Sign in</Link>
            </Button>
          </div>
        </div>

        <HeroShowcase />
      </div>
    </section>
  );
}
