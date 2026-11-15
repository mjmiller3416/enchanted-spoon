import { cleanup, render, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChefNotesCard } from "@/app/(app)/recipes/[id]/_components/ChefNotesCard";

const USDA_URL =
  "https://fdc.nal.usda.gov/fdc-app.html#/food-details/169998/nutrients?query=cornbread-stuffing&nutrients=208,203,204,205,291,301,303,304,305,306,307,601";

describe("Chef's Notes", () => {
  afterEach(() => {
    cleanup();
  });

  it("turns an http(s) URL into a wrapping link and keeps the note inside the card", () => {
    const { container } = render(
      <ChefNotesCard
        notes={`Rest the stuffing 10 minutes so it slices cleanly. Source data: ${USDA_URL}.`}
      />,
    );
    const view = within(container);

    const link = view.getByRole("link", { name: USDA_URL });
    expect(link.getAttribute("href")).toBe(USDA_URL);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.className).toContain("break-words");
    expect(link.className).toContain("[overflow-wrap:anywhere]");

    const paragraph = link.closest("p");
    expect(paragraph?.textContent).toContain("Rest the stuffing 10 minutes so it slices cleanly.");
    expect(paragraph?.textContent?.endsWith(".")).toBe(true);
    expect(paragraph?.className).toContain("break-words");
    expect(paragraph?.className).toContain("[overflow-wrap:anywhere]");

    const column = view.getByRole("heading", { name: "Chef's Notes" }).parentElement;
    expect(column?.className).toContain("min-w-0");
    expect(column?.className).toContain("flex-1");
  });

  it("leaves plain text, including non-http addresses, as text", () => {
    const { container } = render(
      <ChefNotesCard notes="See www.example.com or javascript:alert(1) for nothing." />,
    );
    const view = within(container);
    expect(view.queryByRole("link")).toBeNull();
    expect(view.getByText(/www\.example\.com/)).toBeTruthy();
  });

  it("renders nothing when there are no notes", () => {
    const { container } = render(<ChefNotesCard notes={null} />);
    expect(container.innerHTML).toBe("");
  });
});
