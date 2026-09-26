import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { HomeView } from "@/app/(app)/dashboard/_components/HomeView";

vi.mock("@clerk/nextjs", () => ({ useUser: () => ({ user: { firstName: "Test" } }) }));
vi.mock("@/hooks/api", () => ({
  useDashboardStats: () => ({ data: { total_recipes: 10 }, isLoading: false }),
  usePlannerEntries: () => ({ error: new Error("offline"), isLoading: false, refetch: vi.fn() }),
  useShoppingList: () => ({ data: { total_items: 4 }, isLoading: false }),
}));
vi.mock("@/hooks/persistence", () => ({ useGetStartedComplete: () => [true, vi.fn(), true] }));
vi.mock("@/components/layout/PageLayout", () => ({ PageLayout: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));
vi.mock("@/app/(app)/dashboard/_components/ShoppingListWidget", () => ({ ShoppingListWidget: () => <p>Healthy shopping section</p> }));
vi.mock("@/app/(app)/dashboard/_components/TonightCard", () => ({ TonightCard: () => <p>Meal section</p> }));
vi.mock("@/app/(app)/dashboard/_components/StreakChip", () => ({ StreakChip: () => null }));
vi.mock("@/app/(app)/dashboard/_components/carousel", () => ({ MealCarouselWidget: () => null }));
vi.mock("@/app/(app)/dashboard/_components/GetStartedCard", () => ({ GetStartedCard: () => null, GetStartedBanner: () => null }));

it("keeps healthy shopping content when the planner request fails", () => {
  render(<HomeView />);
  expect(screen.getByText("Healthy shopping section")).toBeTruthy();
  expect(screen.getByText("Couldn’t refresh your meal plan")).toBeTruthy();
  expect(screen.queryByText("Meal section")).toBeNull();
});
