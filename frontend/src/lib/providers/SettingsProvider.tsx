"use client";
import { createContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { settingsApi } from "@/lib/api";
import { accountStorageKey } from "@/lib/account-storage";
import { DEFAULT_SETTINGS, SETTINGS_STORAGE_KEY, type AppSettings, type SettingsPatch } from "@/lib/settings";
import { SettingsStore } from "@/lib/settings-store";

interface SettingsValue {
  settings: AppSettings;
  isLoaded: boolean;
  isLoading: boolean;
  isSyncing: boolean;
  error: string | null;
  retrySave: () => Promise<void>;
  updateSettings: <K extends keyof AppSettings>(section: K, values: Partial<AppSettings[K]>) => void;
  updateMultipleSections: (updates: SettingsPatch) => void;
  resetSettings: () => void;
  resetSection: <K extends keyof AppSettings>(section: K) => void;
}
export const SettingsContext = createContext<SettingsValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const { userId, getToken } = useAuth();
  const [store] = useState(() => new SettingsStore(accountStorageKey(SETTINGS_STORAGE_KEY, userId), {
    get: async () => userId ? settingsApi.get(await getToken()) : {},
    update: async patch => userId ? settingsApi.update(patch as Record<string, unknown>, await getToken()) : patch as Record<string, unknown>,
  }));
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
  useEffect(() => {
    void store.start();
    const refresh = () => { void store.refresh(); };
    // A settings save in another tab triggers a server refresh. Local pending
    // fields take precedence; the backend merges only the submitted fields.
    const storage = (event: StorageEvent) => { if (event.key === accountStorageKey(SETTINGS_STORAGE_KEY, userId)) refresh(); };
    window.addEventListener("focus", refresh);
    window.addEventListener("online", refresh);
    window.addEventListener("storage", storage);
    return () => { store.dispose(); window.removeEventListener("focus", refresh); window.removeEventListener("online", refresh); window.removeEventListener("storage", storage); };
  }, [store, userId]);
  return <SettingsContext.Provider value={{
    ...state, isLoading: !state.isLoaded, retrySave: store.refresh,
    updateSettings: (section, values) => store.update({ [section]: values }),
    updateMultipleSections: store.update,
    // installPrompt is bookkeeping, not a preference — a reset must not re-arm the banner
    resetSettings: () => store.update({ ...DEFAULT_SETTINGS, installPrompt: state.settings.installPrompt }),
    resetSection: section => store.update({ [section]: DEFAULT_SETTINGS[section] }),
  }}>{children}</SettingsContext.Provider>;
}
