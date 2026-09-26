import { afterEach, describe, expect, it } from "vitest";
import { getPostAuthRedirect } from "@/lib/authRedirect";

function visit(search: string) {
  window.history.replaceState(null, "", `/sign-in${search}`);
}

describe("getPostAuthRedirect", () => {
  afterEach(() => visit(""));

  it("defaults to the dashboard", () => {
    visit("");
    expect(getPostAuthRedirect()).toBe("/dashboard");
  });

  it("returns same-origin deep links, absolute or relative", () => {
    visit(`?redirect_url=${encodeURIComponent(`${window.location.origin}/recipes/12?tab=notes`)}`);
    expect(getPostAuthRedirect()).toBe("/recipes/12?tab=notes");
    visit(`?redirect_url=${encodeURIComponent("/meal-planner")}`);
    expect(getPostAuthRedirect()).toBe("/meal-planner");
  });

  it("refuses other origins and protocol-relative URLs", () => {
    visit(`?redirect_url=${encodeURIComponent("https://evil.example/phish")}`);
    expect(getPostAuthRedirect()).toBe("/dashboard");
    visit(`?redirect_url=${encodeURIComponent("//evil.example/phish")}`);
    expect(getPostAuthRedirect()).toBe("/dashboard");
  });

  it("never loops back into auth pages", () => {
    visit(`?redirect_url=${encodeURIComponent("/sign-in")}`);
    expect(getPostAuthRedirect()).toBe("/dashboard");
  });
});
