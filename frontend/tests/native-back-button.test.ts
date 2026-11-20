import { afterEach, expect, it, vi } from "vitest";
import { handleNativeBackButton, decideNativeBackAction } from "@/lib/native/back-button";
import { registerConfirmDismiss } from "@/lib/confirm-dismiss";

afterEach(() => {
  vi.restoreAllMocks();
});

it("decides back from whether a confirmation is open", () => {
  expect(decideNativeBackAction({ confirmOpen: true, canGoBack: true })).toBe("dismiss-dialog");
  expect(decideNativeBackAction({ confirmOpen: true, canGoBack: false })).toBe("dismiss-dialog");
  expect(decideNativeBackAction({ confirmOpen: false, canGoBack: true })).toBe("history-back");
  expect(decideNativeBackAction({ confirmOpen: false, canGoBack: false })).toBe("ignore");
});

it("closes only the top confirmation and does not navigate", () => {
  const back = vi.spyOn(window.history, "back").mockImplementation(() => {});
  const lower = vi.fn();
  const top = vi.fn();
  const stopLower = registerConfirmDismiss(lower);
  const stopTop = registerConfirmDismiss(top);

  expect(handleNativeBackButton({ canGoBack: true })).toBe("dismiss-dialog");
  expect(top).toHaveBeenCalledOnce();
  expect(lower).not.toHaveBeenCalled();
  expect(back).not.toHaveBeenCalled();

  stopTop();
  expect(handleNativeBackButton({ canGoBack: true })).toBe("dismiss-dialog");
  expect(lower).toHaveBeenCalledOnce();
  expect(back).not.toHaveBeenCalled();

  stopLower();
  expect(handleNativeBackButton({ canGoBack: true })).toBe("history-back");
  expect(back).toHaveBeenCalledOnce();
  expect(handleNativeBackButton({ canGoBack: false })).toBe("ignore");
  expect(back).toHaveBeenCalledOnce();
});
