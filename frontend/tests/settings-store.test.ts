import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SettingsStore } from "@/lib/settings-store";
import { DEFAULT_SETTINGS } from "@/lib/settings";
beforeEach(() => { localStorage.clear(); vi.useFakeTimers(); });
afterEach(() => vi.useRealTimers());

it("preserves edits made while the initial response is delayed", async () => {
  let resolve!: (value: Record<string, unknown>) => void;
  const update = vi.fn().mockResolvedValue({ appearance: { theme: "light" } });
  const store = new SettingsStore("a", { get: () => new Promise(r => { resolve = r; }), update });
  const loading = store.start();
  store.update({ appearance: { theme: "light" } });
  resolve({ appearance: { theme: "dark" } });
  await loading;
  expect(store.getSnapshot().settings.appearance.theme).toBe("light");
  expect(update).toHaveBeenCalledWith({ appearance: { theme: "light" } });
});

it("serializes writes and keeps an in-flight batch recoverable while newer edits arrive", async () => {
  let resolve!: (value: Record<string, unknown>) => void;
  const update = vi.fn().mockImplementationOnce(() => new Promise(r => { resolve = r; })).mockResolvedValueOnce({ appearance: { theme: "light" }, aiFeatures: { showAssistantFab: false } });
  const store = new SettingsStore("a", { get: async () => ({}), update });
  await store.start();
  store.update({ appearance: { theme: "light" } });
  const saving = store.flush();
  store.update({ aiFeatures: { showAssistantFab: false } });
  expect(update).toHaveBeenCalledTimes(1);
  expect(JSON.parse(localStorage.getItem("a:pending")!)).toEqual({ appearance: { theme: "light" }, aiFeatures: { showAssistantFab: false } });
  resolve({ appearance: { theme: "light" }, aiFeatures: { showAssistantFab: true } });
  await saving;
  expect(update).toHaveBeenNthCalledWith(2, { aiFeatures: { showAssistantFab: false } });
  expect(store.getSnapshot().settings.aiFeatures.showAssistantFab).toBe(false);
});

it("recovers unsynced settings after reopening and exposes failures", async () => {
  const update = vi.fn().mockRejectedValue(new Error("offline"));
  const first = new SettingsStore("a", { get: async () => ({}), update });
  await first.start();
  first.update({ appearance: { theme: "light" } });
  await first.flush();
  expect(first.getSnapshot().error).toContain("haven't synced");
  first.dispose();
  const recovered = vi.fn().mockResolvedValue({ ...DEFAULT_SETTINGS, appearance: { theme: "light" } });
  const next = new SettingsStore("a", { get: async () => ({ ...DEFAULT_SETTINGS }), update: recovered });
  await next.start();
  await Promise.resolve();
  expect(recovered).toHaveBeenCalledWith({ appearance: { theme: "light" } });
  expect(next.getSnapshot().settings.appearance.theme).toBe("light");
});
