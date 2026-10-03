/**
 * PWA install helpers — platform detection and the deferred Chromium install
 * event. The event is captured by an inline script in the root layout (it can
 * fire before hydration); keep INSTALL_PROMPT_GLOBAL / INSTALL_PROMPT_EVENT in
 * sync with that script.
 */

/** Chromium's install event (not in lib.dom). */
export interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

declare global {
  interface Window {
    __esInstallPrompt?: BeforeInstallPromptEvent | null;
  }
  interface Navigator {
    /** iOS Safari: true when launched from the home screen */
    standalone?: boolean;
  }
}

export const INSTALL_PROMPT_EVENT = "es:installprompt";

/** Banners stop for good after this many dismissals (menu entries remain). */
export const INSTALL_PROMPT_MAX_DISMISSALS = 2;
export const INSTALL_PROMPT_SNOOZE_DAYS = 14;
/** Banners wait for a return visit — never on sign-up day. */
export const INSTALL_PROMPT_MIN_ACCOUNT_AGE_MS = 24 * 60 * 60 * 1000;

export type InstallPlatform = "ios" | "android" | "desktop";

export function detectInstallPlatform(): InstallPlatform {
  const ua = navigator.userAgent;
  // iPadOS 13+ reports a desktop Mac UA; touch support gives it away
  const isIpad = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
  if (/iPhone|iPad|iPod/.test(ua) || isIpad) return "ios";
  if (/Android/.test(ua)) return "android";
  return "desktop";
}

/** True when running as an installed app rather than a browser tab. */
export function isStandaloneDisplay(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    navigator.standalone === true
  );
}

/**
 * Social/email in-app browsers on iOS can't add to the home screen — the page
 * has to be opened in Safari first.
 */
export function isIosInAppBrowser(): boolean {
  return /FBAN|FBAV|Instagram|Line\/|GSA\/|Snapchat|LinkedInApp|Twitter/.test(
    navigator.userAgent
  );
}
