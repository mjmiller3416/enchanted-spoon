"use client";

import { useState, useEffect, useCallback } from "react";

interface UseLocalStorageStateOptions<T> {
  /** Maximum number of items to keep (for array values) */
  maxItems?: number;
  /** Custom deserializer — transform raw parsed JSON into the desired shape */
  deserialize?: (raw: unknown) => T;
  /** Old key to migrate from on mount (pre-rename shim; see migrateLocalStorageKey) */
  legacyKey?: string;
}

/**
 * One-time key-rename shim: if `legacyKey` holds a value, copy it to `key`
 * (unless `key` already has one) and delete the legacy entry. Idempotent.
 * Shim call sites can be dropped 1–2 releases after the rename ships.
 */
export function migrateLocalStorageKey(legacyKey: string, key: string): void {
  if (typeof window === "undefined") return;
  try {
    const legacy = localStorage.getItem(legacyKey);
    if (legacy === null) return;
    if (localStorage.getItem(key) === null) {
      localStorage.setItem(key, legacy);
    }
    localStorage.removeItem(legacyKey);
  } catch {
    // localStorage unavailable — nothing to migrate
  }
}

/**
 * Generic hook for state persisted to localStorage with cross-tab
 * and same-window synchronization via CustomEvent + StorageEvent.
 *
 * @param key - localStorage key
 * @param initialValue - Default value when nothing is stored
 * @param options - Optional configuration
 * @returns [state, setState, isLoaded] tuple
 */
export function useLocalStorageState<T>(
  key: string,
  initialValue: T,
  options: UseLocalStorageStateOptions<T> = {}
): [T, (value: T | ((prev: T) => T)) => void, boolean] {
  const { maxItems, deserialize, legacyKey } = options;
  const eventName = `localStorage:${key}`;

  const [state, setStateInternal] = useState<T>(initialValue);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      if (legacyKey) {
        migrateLocalStorageKey(legacyKey, key);
      }
      const stored = localStorage.getItem(key);
      if (stored) {
        const parsed = JSON.parse(stored);
        const value = deserialize ? deserialize(parsed) : parsed;
        // Post-mount hydration from localStorage: the first render must match
        // the server (initialValue), then this one-time sync loads the stored
        // value. Consumers gate on isLoaded, so the extra render is the point.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setStateInternal(value);
      }
    } catch (err) {
      console.error(`[useLocalStorageState] Failed to load ${key}:`, err);
    }
    setIsLoaded(true);
  }, [key, deserialize, legacyKey]);

  // Listen for changes from other tabs (StorageEvent) and same window (CustomEvent)
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === key && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          const value = deserialize ? deserialize(parsed) : parsed;
          setStateInternal(value);
        } catch (err) {
          console.error(`[useLocalStorageState] Failed to parse ${key}:`, err);
        }
      }
    };

    const handleCustom = (e: Event) => {
      const customEvent = e as CustomEvent<T>;
      setStateInternal(customEvent.detail);
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener(eventName, handleCustom);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener(eventName, handleCustom);
    };
  }, [key, eventName, deserialize]);

  const setState = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStateInternal((prev) => {
        const next = typeof value === "function" ? (value as (prev: T) => T)(prev) : value;
        const toStore = maxItems && Array.isArray(next) ? next.slice(-maxItems) : next;
        try {
          localStorage.setItem(key, JSON.stringify(toStore));
          // Defer event dispatch to avoid "setState during render" errors
          // when multiple components use this hook simultaneously
          queueMicrotask(() => {
            window.dispatchEvent(new CustomEvent(eventName, { detail: toStore }));
          });
        } catch (err) {
          console.error(`[useLocalStorageState] Failed to save ${key}:`, err);
        }
        return toStore as T;
      });
    },
    [key, eventName, maxItems]
  );

  return [state, setState, isLoaded];
}
