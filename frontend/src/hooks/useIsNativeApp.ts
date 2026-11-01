"use client";

import { useSyncExternalStore } from "react";
import { isNativeApp } from "@/lib/native/platform";

function subscribe() {
  return () => {};
}

function getClientSnapshot() {
  return isNativeApp();
}

function getServerSnapshot() {
  return false;
}

/**
 * False on the server and during hydration. True only when this page is
 * running inside the Capacitor shell.
 */
export function useIsNativeApp() {
  return useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);
}
