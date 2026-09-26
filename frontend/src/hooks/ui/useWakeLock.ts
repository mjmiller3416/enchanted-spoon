"use client";
import { useCallback, useEffect, useState } from "react";

export function useWakeLock() {
  const [isSupported] = useState(() => typeof navigator !== "undefined" && "wakeLock" in navigator);
  const [isActive, setActive] = useState(false);
  const [isHeld, setHeld] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!isActive || !isSupported) return;
    let cancelled = false;
    let pending = false;
    let lock: WakeLockSentinel | null = null;
    const acquire = async () => {
      if (cancelled || pending || lock || document.visibilityState !== "visible") return;
      pending = true;
      try {
        const acquired = await navigator.wakeLock.request("screen");
        if (cancelled) { await acquired.release(); return; }
        lock = acquired;
        setHeld(!acquired.released);
        setError(null);
        acquired.addEventListener("release", () => { lock = null; if (!cancelled) setHeld(false); });
      } catch {
        if (!cancelled) { setHeld(false); setError("Your browser couldn't keep the screen awake."); }
      } finally { pending = false; }
    };
    void acquire();
    document.addEventListener("visibilitychange", acquire);
    return () => { cancelled = true; document.removeEventListener("visibilitychange", acquire); void lock?.release().catch(() => undefined); };
  }, [isActive, isSupported]);
  const enable = useCallback(() => setActive(true), []);
  const disable = useCallback(() => { setActive(false); setHeld(false); setError(null); }, []);
  const toggle = useCallback(() => { setActive(value => !value); setHeld(false); setError(null); }, []);
  return { isSupported, isActive, isHeld, error, enable, disable, toggle };
}
