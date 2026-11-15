import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketingHeader } from "@/app/(marketing)/_components/MarketingHeader";

describe("marketing header safe area", () => {
  it("pads the sticky bar by the top safe-area inset", () => {
    render(<MarketingHeader />);
    const header = screen.getByRole("banner");
    expect(header.className).toContain("pt-[env(safe-area-inset-top,0px)]");
    expect(header.className).toContain("sticky");
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Start free" })).toBeTruthy();
  });
});
