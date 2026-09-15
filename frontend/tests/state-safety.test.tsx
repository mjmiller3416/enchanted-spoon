import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, renderHook, screen, waitFor } from "@testing-library/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { useChatHistory } from "@/hooks/persistence/useChatHistory";
import { useToggleFavorite } from "@/hooks/api/useRecipes";
import { recipeQueryKeys } from "@/hooks/api/queryKeys";
import { useEffect, type ReactNode } from "react";

const mocks = vi.hoisted(() => ({
  userId: "account-a" as string | null,
  toggleFavorite: vi.fn(),
}));
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ userId: mocks.userId, isLoaded: true, isSignedIn: !!mocks.userId, getToken: async () => "test" }) }));
vi.mock("@/lib/paywall", () => ({ maybeHandleAiGateError: vi.fn() }));
vi.mock("@/lib/api", () => ({ recipeApi: { toggleFavorite: mocks.toggleFavorite } }));

const wrapper = ({ children }: { children: ReactNode }) => <QueryProvider>{children}</QueryProvider>;
afterEach(cleanup);
beforeEach(() => { localStorage.clear(); mocks.userId = "account-a"; vi.clearAllMocks(); });

describe("state safety", () => {
  it("does not automatically repeat a write after a lost response", async () => {
    const write = vi.fn().mockRejectedValue(new Error("response lost after commit"));
    const { result } = renderHook(() => useMutation({ mutationFn: write }), { wrapper });
    await act(async () => { await result.current.mutateAsync(undefined).catch(() => undefined); });
    expect(write).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("retires cached and component state when the account changes", async () => {
    let previousClient: ReturnType<typeof useQueryClient>;
    function Reader() {
      const client = useQueryClient();
      useEffect(() => { if (mocks.userId === "account-a") previousClient = client; }, [client]);
      const { data } = useQuery({ queryKey: ["private"], queryFn: async () => "unused", enabled: false, initialData: mocks.userId === "account-a" ? "A recipe" : undefined });
      return <p>{data ?? "No private data"}</p>;
    }
    const view = render(<QueryProvider><Reader /></QueryProvider>);
    expect(screen.getByText("A recipe")).toBeTruthy();
    mocks.userId = "account-b";
    view.rerender(<QueryProvider><Reader /></QueryProvider>);
    // Even a late write into the retired cache cannot affect B.
    previousClient!.setQueryData(["private"], "Late A response");
    expect(screen.getByText("No private data")).toBeTruthy();
    expect(screen.queryByText("A recipe")).toBeNull();
  });

  it("keeps chat history per account and does not claim unowned legacy history", async () => {
    localStorage.setItem("enchanted-spoon-chat-history", JSON.stringify([{ role: "user", content: "legacy secret" }]));
    function History() {
      const { messages, addMessage } = useChatHistory();
      return <><p>{messages.map(m => m.content).join(",") || "Empty history"}</p><button onClick={() => addMessage({ role: "user", content: "A message" })}>Add</button></>;
    }
    const view = render(<QueryProvider><History /></QueryProvider>);
    expect(screen.queryByText("legacy secret")).toBeNull();
    await act(async () => screen.getByText("Add").click());
    mocks.userId = "account-b";
    view.rerender(<QueryProvider><History /></QueryProvider>);
    expect(screen.getByText("Empty history")).toBeTruthy();
    mocks.userId = "account-a";
    view.rerender(<QueryProvider><History /></QueryProvider>);
    await waitFor(() => expect(screen.getByText("A message")).toBeTruthy());
  });

  it("saves favorite state through the API and updates both detail and library", async () => {
    mocks.toggleFavorite.mockResolvedValue({ id: 7, is_favorite: true });
    const { result } = renderHook(() => ({ mutation: useToggleFavorite(), client: useQueryClient() }), { wrapper });
    result.current.client.setQueryData(recipeQueryKeys.list(), [{ id: 7, is_favorite: false }, { id: 8, is_favorite: true }]);
    await act(async () => { await result.current.mutation.mutateAsync(7); });
    expect(mocks.toggleFavorite).toHaveBeenCalledWith(7, "test");
    expect(result.current.client.getQueryData(recipeQueryKeys.detail(7))).toEqual({ id: 7, is_favorite: true });
    expect(result.current.client.getQueryData(recipeQueryKeys.list())).toEqual([{ id: 7, is_favorite: true }, { id: 8, is_favorite: true }]);
  });
});
