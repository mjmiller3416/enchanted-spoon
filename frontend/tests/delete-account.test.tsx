import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { createRouteMatcher } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";
import DeleteAccountPage, { metadata } from "@/app/(marketing)/delete-account/page";
import { publicRoutePatterns } from "@/proxy";

const isPublicRoute = createRouteMatcher(publicRoutePatterns);

function request(path: string) {
  return new NextRequest(new URL(path, "http://localhost:3000"));
}

describe("public account deletion page", () => {
  it("treats /delete-account as public and keeps the app signed-in", () => {
    expect(publicRoutePatterns).toContain("/delete-account(.*)");
    expect(isPublicRoute(request("/delete-account"))).toBe(true);
    expect(isPublicRoute(request("/settings"))).toBe(false);
    expect(isPublicRoute(request("/privacy"))).toBe(true);
  });

  it("uses the in-app labels, support email, and deletion headings", () => {
    expect(metadata.title).toBe("Delete your Enchanted Spoon account");
    render(<DeleteAccountPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Delete your Enchanted Spoon account" }),
    ).toBeTruthy();
    expect(screen.getByText("Account & Profile")).toBeTruthy();
    expect(screen.getByText("Delete Account")).toBeTruthy();
    expect(screen.getByText("Data Management")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "info@enchantedspoon.app" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "What data is deleted" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What may be retained" })).toBeTruthy();
    expect(screen.getAllByText(/within 30 days/).length).toBeGreaterThan(0);
  });
});
