"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useEffectEvent,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useUser } from "@clerk/nextjs";
import { useSettings } from "@/hooks/persistence/useSettings";
import { useTour } from "@/lib/providers/TourProvider";
import { IosInstallSheet } from "@/components/common/IosInstallSheet";
import {
  INSTALL_PROMPT_EVENT,
  INSTALL_PROMPT_MAX_DISMISSALS,
  INSTALL_PROMPT_MIN_ACCOUNT_AGE_MS,
  INSTALL_PROMPT_SNOOZE_DAYS,
  detectInstallPlatform,
  isStandaloneDisplay,
} from "@/lib/pwa";

interface PwaInstallContextValue {
  /** An install entry point makes sense here (menu items) */
  canInstall: boolean;
  /** A proactive banner may show right now (phone, return visit, not snoozed) */
  showBanner: boolean;
  /** Native prompt on Chromium; the Add to Home Screen sheet on iOS */
  install: () => Promise<void>;
  /** "Not now" — snoozes banners; they stop for good after a second dismissal */
  dismissBanner: () => void;
}

const PwaInstallContext = createContext<PwaInstallContextValue | null>(null);

const noopSubscribe = () => () => {};

function subscribeDisplayMode(notify: () => void) {
  const media = window.matchMedia("(display-mode: standalone)");
  media.addEventListener("change", notify);
  return () => media.removeEventListener("change", notify);
}

function subscribeDeferredPrompt(notify: () => void) {
  window.addEventListener(INSTALL_PROMPT_EVENT, notify);
  return () => window.removeEventListener(INSTALL_PROMPT_EVENT, notify);
}

const getDeferredPrompt = () => window.__esInstallPrompt ?? null;

/** The Chromium event is single-use; drop it once spent or the app installs. */
function clearDeferredPrompt() {
  window.__esInstallPrompt = null;
  window.dispatchEvent(new Event(INSTALL_PROMPT_EVENT));
}

/**
 * PwaInstallProvider — one source of truth for "can this device install the
 * app, and should we ask right now?" Menu items read `canInstall`; Home and
 * Shopping banners read `showBanner`. Banners never appear on sign-up day or
 * during the tour, snooze for two weeks on dismissal, and retire after the
 * second dismissal. Installed state is account-synced so an iOS home-screen
 * launch also silences Safari.
 */
export function PwaInstallProvider({ children }: { children: ReactNode }) {
  const { user } = useUser();
  const { isActive: tourActive } = useTour();
  const { settings, isLoaded, updateSettings } = useSettings();
  const { installedAt, dismissCount, snoozedUntil } = settings.installPrompt;

  const platform = useSyncExternalStore(noopSubscribe, detectInstallPlatform, () => null);
  const standalone = useSyncExternalStore(subscribeDisplayMode, isStandaloneDisplay, () => false);
  const deferredPrompt = useSyncExternalStore(subscribeDeferredPrompt, getDeferredPrompt, () => null);
  const [iosSheetOpen, setIosSheetOpen] = useState(false);
  const [mountedAt] = useState(() => Date.now());

  const recordInstalled = useEffectEvent(() => {
    if (!installedAt) {
      updateSettings("installPrompt", { installedAt: new Date().toISOString() });
    }
  });

  // Launched from the home screen → remember it on the account
  useEffect(() => {
    if (standalone && isLoaded) recordInstalled();
  }, [standalone, isLoaded]);

  useEffect(() => {
    const onInstalled = () => {
      clearDeferredPrompt();
      recordInstalled();
    };
    window.addEventListener("appinstalled", onInstalled);
    return () => window.removeEventListener("appinstalled", onInstalled);
  }, []);

  const dismissBanner = useCallback(() => {
    const snoozeMs = INSTALL_PROMPT_SNOOZE_DAYS * 24 * 60 * 60 * 1000;
    updateSettings("installPrompt", {
      dismissCount: dismissCount + 1,
      snoozedUntil: new Date(Date.now() + snoozeMs).toISOString(),
    });
  }, [dismissCount, updateSettings]);

  const install = useCallback(async () => {
    if (deferredPrompt) {
      clearDeferredPrompt();
      try {
        await deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        // "accepted" is recorded by the appinstalled listener
        if (outcome === "dismissed") dismissBanner();
      } catch {
        // Event already spent (another tab/menu used it) — nothing to show
      }
      return;
    }
    if (platform === "ios") setIosSheetOpen(true);
  }, [deferredPrompt, platform, dismissBanner]);

  const canInstall = !standalone && (deferredPrompt !== null || platform === "ios");

  const createdAt = user?.createdAt?.getTime();
  const returningUser =
    createdAt !== undefined && mountedAt - createdAt >= INSTALL_PROMPT_MIN_ACCOUNT_AGE_MS;
  const snoozed = snoozedUntil !== null && Date.parse(snoozedUntil) > mountedAt;

  const showBanner =
    canInstall &&
    platform !== "desktop" &&
    isLoaded &&
    !installedAt &&
    dismissCount < INSTALL_PROMPT_MAX_DISMISSALS &&
    !snoozed &&
    returningUser &&
    !tourActive;

  const value = useMemo(
    () => ({ canInstall, showBanner, install, dismissBanner }),
    [canInstall, showBanner, install, dismissBanner]
  );

  return (
    <PwaInstallContext.Provider value={value}>
      {children}
      <IosInstallSheet open={iosSheetOpen} onOpenChange={setIosSheetOpen} />
    </PwaInstallContext.Provider>
  );
}

export function usePwaInstall(): PwaInstallContextValue {
  const value = useContext(PwaInstallContext);
  if (!value) throw new Error("usePwaInstall requires PwaInstallProvider");
  return value;
}
