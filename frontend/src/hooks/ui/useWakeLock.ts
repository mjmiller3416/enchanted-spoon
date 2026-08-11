"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseWakeLockReturn {
  /** Whether the Screen Wake Lock API exists in this browser (secure context, iOS 16.4+, Chrome/Android). */
  isSupported: boolean;
  /** Whether the caller has requested the lock stay on. Reflects intent, not the live sentinel. */
  isActive: boolean;
  /** Turn the wake lock on. */
  enable: () => void;
  /** Turn the wake lock off and release any held sentinel. */
  disable: () => void;
  /** Flip the current state. */
  toggle: () => void;
}

/**
 * Keeps the device screen awake while active — for following a recipe hands-free.
 *
 * Wraps the Screen Wake Lock API (`navigator.wakeLock`). Two behaviours matter:
 *
 * 1. The OS automatically releases the lock whenever the tab is hidden or the
 *    screen is manually locked. We listen for `visibilitychange` and re-acquire
 *    when the page becomes visible again, so switching apps and returning
 *    doesn't silently stop it.
 * 2. It's a progressive enhancement — `isSupported` is false on browsers without
 *    the API (older iOS, insecure contexts). Callers should hide their toggle
 *    when unsupported rather than show a dead control.
 */
export function useWakeLock(): UseWakeLockReturn {
  // Feature-detect once. The initializer runs per environment: false during SSR
  // (no navigator), the real answer on the client. Support never changes within
  // a session, so this needs no effect or state updates.
  const [isSupported] = useState(
    () => typeof navigator !== "undefined" && "wakeLock" in navigator,
  );
  const [isActive, setIsActive] = useState(false);
  const sentinelRef = useRef<WakeLockSentinel | null>(null);

  const releaseSentinel = useCallback(async () => {
    const sentinel = sentinelRef.current;
    sentinelRef.current = null;
    if (sentinel) {
      try {
        await sentinel.release();
      } catch {
        // Already released (e.g. by the OS) — nothing to do.
      }
    }
  }, []);

  const acquireSentinel = useCallback(async () => {
    // Guard: still wanted, supported, page visible, and not already held.
    if (
      !("wakeLock" in navigator) ||
      document.visibilityState !== "visible" ||
      sentinelRef.current
    ) {
      return;
    }
    try {
      const sentinel = await navigator.wakeLock.request("screen");
      sentinelRef.current = sentinel;
      // The OS may drop the lock on its own; drop our reference so the
      // visibilitychange handler knows to re-acquire.
      sentinel.addEventListener("release", () => {
        if (sentinelRef.current === sentinel) {
          sentinelRef.current = null;
        }
      });
    } catch {
      // Request can reject (e.g. low battery); leave isActive so we retry
      // on the next visibilitychange.
    }
  }, []);

  const enable = useCallback(() => setIsActive(true), []);
  const disable = useCallback(() => setIsActive(false), []);
  const toggle = useCallback(() => setIsActive((prev) => !prev), []);

  // Drive the actual lock from the desired `isActive` state.
  useEffect(() => {
    if (!isActive) {
      void releaseSentinel();
      return;
    }

    void acquireSentinel();

    // Re-acquire whenever the page returns to the foreground.
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        void acquireSentinel();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      void releaseSentinel();
    };
  }, [isActive, acquireSentinel, releaseSentinel]);

  return { isSupported, isActive, enable, disable, toggle };
}
