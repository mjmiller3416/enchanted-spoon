import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { shoppingQueryKeys, useToggleItem } from "@/hooks/api/useShopping";
import type { ShoppingListResponseDTO } from "@/types/shopping";

const mocks = vi.hoisted(() => ({ update: vi.fn() }));
vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ getToken: async () => "test" }) }));
vi.mock("@/lib/api", () => ({ shoppingApi: { updateItem: mocks.update } }));

it("a failed item update cannot roll back a different collected item", async () => {
  let failFirst!: (reason: Error) => void;
  mocks.update.mockImplementation((id: number) => id === 1
    ? new Promise((_resolve, reject) => { failFirst = reject; })
    : Promise.resolve({ id, have: true }));
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  client.setQueryData(shoppingQueryKeys.list(), { items: [{ id: 1, have: false }, { id: 2, have: false }], checked_items: 0 });
  const { result } = renderHook(() => useToggleItem(), { wrapper: ({ children }) => <QueryClientProvider client={client}>{children}</QueryClientProvider> });
  act(() => { result.current.mutate({ id: 1, value: true }); });
  await waitFor(() => expect(mocks.update).toHaveBeenCalledTimes(1));
  await act(async () => { await result.current.mutateAsync({ id: 2, value: true }); });
  await act(async () => { failFirst(new Error("response lost")); });
  await waitFor(() => {
    const data = client.getQueryData<ShoppingListResponseDTO>(shoppingQueryKeys.list())!;
    expect(data.items.map(item => item.have)).toEqual([false, true]);
    expect(data.checked_items).toBe(1);
  });
  expect(mocks.update).toHaveBeenCalledWith(2, { have: true }, "test");
});
