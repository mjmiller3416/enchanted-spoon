import Link from "next/link";
import { ChefHat, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * 404 Not Found state for when a recipe doesn't exist.
 * Displays a friendly message and a link back to the recipes list.
 */
export function RecipeNotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen px-6 bg-background">
      <div className="max-w-md text-center">
        <div className="flex items-center justify-center w-24 h-24 mx-auto mb-6 rounded-full bg-elevated">
          <ChefHat className="w-12 h-12 text-muted-foreground" />
        </div>
        <h1 className="mb-3 text-3xl font-bold text-foreground">
          Recipe Not Found
        </h1>
        <p className="mb-8 text-muted-foreground">
          Sorry, we couldn&apos;t find the recipe you&apos;re looking for. It may have been
          deleted or the link might be incorrect.
        </p>
        <Link href="/recipes">
          <Button className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Recipes
          </Button>
        </Link>
      </div>
    </div>
  );
}
