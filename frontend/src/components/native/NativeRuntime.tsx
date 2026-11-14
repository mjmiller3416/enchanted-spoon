"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { useCurrentUser } from "@/hooks/api";
import { mayMentionWebFoundingOffer } from "@/lib/native/founding-offer";
import { isNativeApp, nativePlatform } from "@/lib/native/platform";
import { importUrlFromDeepLink, isOAuthCallback } from "@/lib/native/share-link";

const STOREFRONT_CLASS = "ios-storefront-us";

function reportNativeLoadError(message: string, reason: unknown): void {
  Sentry.captureException(reason instanceof Error ? reason : new Error(message));
}

/**
 * Behavior that only applies inside the Capacitor shell: system browser for
 * external links, splash dismissal, store customer identity, and the US
 * App Store exception for a link to the web founding price.
 */
export function NativeRuntime() {
  useEffect(() => {
    if (!isNativeApp()) return;

    const root = document.documentElement;
    root.classList.add("native-app", `native-${nativePlatform()}`);

    let removeClick = () => {};
    let removeUrl: (() => void) | undefined;
    let cancelled = false;

    void (async () => {
      const [{ App }, { Browser }, { SplashScreen }] = await Promise.all([
        import("@capacitor/app"),
        import("@capacitor/browser"),
        import("@capacitor/splash-screen"),
      ]);
      if (cancelled) return;
      void SplashScreen.hide().catch(() => undefined);

      const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = (event.target as HTMLElement | null)?.closest?.("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#")) return;

      let url: URL;
      try {
        url = new URL(anchor.href);
      } catch {
        return;
      }

      const externalPurchase = anchor.dataset.externalPurchase === "true";
      const leavesApp =
        externalPurchase ||
        (url.origin !== window.location.origin &&
          (url.protocol === "https:" || url.protocol === "http:"));
      if (!leavesApp) return;

        event.preventDefault();
        void Browser.open({ url: url.toString() });
      };

      document.addEventListener("click", onClick);
      removeClick = () => document.removeEventListener("click", onClick);
      const handle = await App.addListener("appUrlOpen", (event) => {
        void Browser.close().catch(() => undefined);
        if (isOAuthCallback(event.url)) {
          const incoming = new URL(event.url);
          const next = new URL("/sso-callback", window.location.origin);
          next.search = incoming.search;
          window.location.assign(next.toString());
          return;
        }
        const shared = importUrlFromDeepLink(event.url);
        if (shared) {
          window.dispatchEvent(new CustomEvent("enchantedspoon:import", { detail: shared }));
        }
      });
      if (cancelled) {
        void handle.remove();
        return;
      }
      removeUrl = () => {
        void handle.remove();
      };
    })().catch((reason: unknown) => {
      reportNativeLoadError("Failed to load the native app runtime", reason);
    });

    return () => {
      cancelled = true;
      removeClick();
      removeUrl?.();
    };
  }, []);

  useEffect(() => {
    if (nativePlatform() !== "ios") return;
    let cancelled = false;
    void import("@/lib/native/purchases")
      .then(({ loadAppleStorefrontCountry }) =>
        loadAppleStorefrontCountry().then((country) => {
          if (cancelled) return;
          const allowed = mayMentionWebFoundingOffer("ios", country);
          document.documentElement.classList.toggle(STOREFRONT_CLASS, allowed);
        }),
      )
      .catch((reason: unknown) => {
        reportNativeLoadError("Failed to load the native storefront", reason);
      });
    return () => {
      cancelled = true;
      document.documentElement.classList.remove(STOREFRONT_CLASS);
    };
  }, []);

  return null;
}

/**
 * Links the store customer to our account id. Mounted only inside the
 * signed-in app so public pages are not forced through Clerk during prerender.
 */
export function IdentifyStoreAccount() {
  const { data: user } = useCurrentUser();
  const userId = user?.id;

  useEffect(() => {
    if (!isNativeApp() || userId == null) return;
    let cancelled = false;
    void import("@/lib/native/purchases")
      .then(({ identifyStoreCustomer }) => {
        if (!cancelled) return identifyStoreCustomer(userId).catch(() => undefined);
      })
      .catch((reason: unknown) => {
        reportNativeLoadError("Failed to load the native purchases module", reason);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  return null;
}
