/**
 * Detect the Capacitor shell. The hosted Next.js app is what the WebView
 * loads, and the native shell injects `window.Capacitor` before our script
 * runs. Importing `@capacitor/core` here would pull that package into every
 * server render that touches the API client, so this file only reads the
 * injected global.
 */

interface CapacitorGlobal {
  isNativePlatform?: () => boolean;
  getPlatform?: () => string;
}

declare global {
  interface Window {
    Capacitor?: CapacitorGlobal;
  }
}

export type NativePlatform = "ios" | "android" | "web";

export function isNativeApp(): boolean {
  if (typeof window === "undefined") return false;
  return window.Capacitor?.isNativePlatform?.() === true;
}

export function nativePlatform(): NativePlatform {
  if (!isNativeApp()) return "web";
  const platform = window.Capacitor?.getPlatform?.();
  if (platform === "ios" || platform === "android") return platform;
  return "web";
}

/** Header the API uses to refuse Stripe Checkout inside the native shell. */
export function nativeClientHeaders(): Record<string, string> {
  const platform = nativePlatform();
  if (platform === "web") return {};
  return { "X-Enchanted-Spoon-Client": `native-${platform}` };
}
