import { useEffect } from "react";
import { act, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { AssistantProvider, useAssistantDialog } from "@/lib/providers/AssistantProvider";

const mocks = vi.hoisted(() => ({ chat: vi.fn(), add: vi.fn() }));
vi.mock("@/hooks/api/useAI", () => ({ useAssistantChat: () => ({ mutateAsync: mocks.chat, isPending: false }) }));
vi.mock("@/hooks/persistence/useChatHistory", () => ({ useChatHistory: () => ({ messages: [], addMessage: mocks.add, clearHistory: vi.fn() }) }));
vi.mock("@/lib/paywall", () => ({ classifyAiGateError: () => false }));

it("retains a draft that arrives while the popup is closed, without another AI request", async () => {
  let finish!: (value: unknown) => void;
  mocks.chat.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  let session!: ReturnType<typeof useAssistantDialog>;
  function Popup() { const value = useAssistantDialog(); useEffect(() => { session = value; }, [value]); return <p>{value.pendingRecipe ? "Draft ready" : "No draft"}</p>; }
  const view = render(<AssistantProvider><Popup /></AssistantProvider>);
  let pending!: Promise<void>;
  act(() => { pending = session.sendMessage("Create a recipe"); });
  view.rerender(<AssistantProvider>{null}</AssistantProvider>);
  await act(async () => { finish({ success: true, recipe: { recipe_name: "Test recipe" }, response: "Ready" }); await pending; });
  view.rerender(<AssistantProvider><Popup /></AssistantProvider>);
  expect(screen.getByText("Draft ready")).toBeTruthy();
  expect(mocks.chat).toHaveBeenCalledTimes(1);
});
