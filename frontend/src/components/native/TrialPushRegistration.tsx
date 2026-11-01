"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useCurrentUser } from "@/hooks/api";
import { isNativeApp, nativePlatform } from "@/lib/native/platform";

const ASKED_KEY = "enchanted-spoon-push-asked";

/**
 * Asks for notification permission only after a trial has started, then
 * registers the APNs/FCM token with the account.
 */
export function TrialPushRegistration() {
  const { data: user } = useCurrentUser();
  const { getToken } = useAuth();
  const trialing =
    user?.subscription_status === "trialing" || user?.store_status === "trialing";

  useEffect(() => {
    if (!isNativeApp() || !trialing || user == null) return;
    if (window.localStorage.getItem(ASKED_KEY) === "1") return;

    let cancelled = false;
    void (async () => {
      const { PushNotifications } = await import("@capacitor/push-notifications");
      const permission = await PushNotifications.requestPermissions();
      window.localStorage.setItem(ASKED_KEY, "1");
      if (cancelled || permission.receive !== "granted") return;
      await PushNotifications.register();
      await PushNotifications.addListener("registration", (event) => {
        const platform = nativePlatform();
        if (platform === "web") return;
        void getToken().then((token) =>
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/devices`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
              "X-Enchanted-Spoon-Client": `native-${platform}`,
            },
            body: JSON.stringify({ token: event.value, platform }),
          }),
        );
      });
    })().catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [getToken, trialing, user]);

  return null;
}
