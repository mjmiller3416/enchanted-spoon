import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

function source(path: string): string {
  return readFileSync(join(process.cwd(), path), "utf8");
}

const css = source("src/app/globals.css");

describe("large Android layout", () => {
  it("insets the recipe editor on tablets and keeps short landscape full screen", () => {
    expect(css).toContain("width: min(72rem, calc(100% - 3rem))");
    expect(css).not.toContain("width: calc(100vw - 3rem)");
    expect(css).toContain("(min-width: 40rem) and (min-height: 32rem)");
    const editor = css.slice(css.indexOf("@utility editor-dialog"), css.indexOf("@utility menu-with-detail"));
    expect(editor).toContain("min-height: 32rem");
    expect(editor).toContain("height: 100dvh");
  });

  it("keeps the floating Genie below the top nav, and full screen when the screen is short", () => {
    const popup = source("src/components/assistant/AssistantPopup.tsx");
    expect(popup).toContain('"(max-width: 767px), (max-height: 32rem)"');
    expect(popup).toContain("sm:max-w-full");
    expect(css).toContain("max-height: calc(100dvh - 4rem - 1.5rem)");
    expect(css).toContain("(width < 48rem), (height < 32rem)");
  });

  it("uses three recipe columns from tablet width, with card stats that wrap instead of clipping", () => {
    expect(source("src/components/recipe/RecipeCard.tsx")).toContain(
      "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4",
    );
    expect(source("src/components/recipe/browser/RecipeBrowserSkeleton.tsx")).toContain(
      "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4",
    );
    expect(source("src/components/recipe/RecipeCard.tsx")).toContain("flex-wrap");
    expect(source("src/components/recipe/RecipeCard.tsx")).toContain("@container");
  });

  it("stacks recipe creation choices on a short landscape phone", () => {
    const step = source("src/app/(app)/recipes/_components/wizard/steps/MethodSelectionStep.tsx");
    expect(step).toContain("[@media(max-height:32rem)]:grid-cols-1");
    expect(step).toContain("[@media(max-height:32rem)]:flex-row");
  });
});
