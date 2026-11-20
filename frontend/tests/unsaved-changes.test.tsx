import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { useUnsavedChanges, hasAnyUnsavedChanges, setNavigationBypass } from "@/hooks/ui/useUnsavedChanges";
import { registerConfirmDismiss } from "@/lib/confirm-dismiss";
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/recipes" }));
afterEach(() => { cleanup(); setNavigationBypass(false); });

it("keeps a dirty editor registered when a second clean overlay mounts and unmounts", () => {
  const dirty = renderHook(() => useUnsavedChanges({ isDirty: true }));
  const clean = renderHook(() => useUnsavedChanges({ isDirty: false }));
  expect(hasAnyUnsavedChanges()).toBe(true);
  clean.unmount();
  expect(hasAnyUnsavedChanges()).toBe(true);
  dirty.unmount();
  expect(hasAnyUnsavedChanges()).toBe(false);
});

it("warns before refresh only while the editor has unsaved changes", () => {
  const view = renderHook(({ dirty }) => useUnsavedChanges({ isDirty: dirty }), { initialProps: { dirty: true } });
  const first = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(first);
  expect(first.defaultPrevented).toBe(true);
  view.rerender({ dirty: false });
  const saved = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(saved);
  expect(saved.defaultPrevented).toBe(false);
});

it("asks before leaving on back when no confirmation is open", () => {
  const discard = vi.fn();
  const view = renderHook(() => useUnsavedChanges({ isDirty: true, onConfirmLeave: discard }));
  act(() => { window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(view.result.current.showLeaveDialog).toBe(true);
  expect(discard).not.toHaveBeenCalled();
  view.unmount();
});

it("closes an open confirmation on back without discarding the draft", () => {
  const discard = vi.fn();
  const dismiss = vi.fn();
  const unregister = registerConfirmDismiss(dismiss);
  const view = renderHook(() => useUnsavedChanges({ isDirty: true, onConfirmLeave: discard }));
  try {
    act(() => { window.dispatchEvent(new PopStateEvent("popstate")); });
    expect(dismiss).toHaveBeenCalledOnce();
    expect(discard).not.toHaveBeenCalled();
    expect(view.result.current.showLeaveDialog).toBe(false);
  } finally {
    unregister();
    view.unmount();
  }
});

it("runs only dirty editor discard handlers on confirmed cross-page navigation", async () => {
  const { discardUnsavedChanges } = await import("@/hooks/ui/useUnsavedChanges");
  const discard = vi.fn();
  const clean = vi.fn();
  renderHook(() => useUnsavedChanges({ isDirty: true, onConfirmLeave: discard }));
  renderHook(() => useUnsavedChanges({ isDirty: false, onConfirmLeave: clean }));
  discardUnsavedChanges();
  expect(discard).toHaveBeenCalledTimes(1);
  expect(clean).not.toHaveBeenCalled();
});
