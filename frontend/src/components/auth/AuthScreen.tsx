import type { ReactNode } from "react";
import { Logo } from "@/components/layout/Logo";

/**
 * Auth pages used to center a card in a `min-h-screen` (100vh) flex box.
 * On a short landscape phone 100vh is taller than the visible viewport, so
 * the centered card overflows above the scroll origin and the submit button
 * is clipped. Size to the dynamic/small viewport instead, and let overflow
 * scroll. Auto margins center the card only while it fits.
 *
 * Horizontal and vertical padding is at least 1rem, and grows to the
 * Capacitor / Safari safe-area inset when one is present. A zero inset
 * (desktop, and the native shell's automatic content inset) keeps 1rem.
 * Under 500px of height the vertical padding tightens so the form can fit.
 */
export const authScreenClassName = [
  "flex w-full min-h-[100dvh] flex-col overflow-x-clip overflow-y-auto bg-background",
  "supports-[height:100svh]:min-h-[100svh]",
  "pl-[max(1rem,env(safe-area-inset-left,0px))]",
  "pr-[max(1rem,env(safe-area-inset-right,0px))]",
  "pt-[max(1rem,env(safe-area-inset-top,0px))]",
  "pb-[max(1rem,env(safe-area-inset-bottom,0px))]",
  "[@media(max-height:500px)]:pt-[max(0.5rem,env(safe-area-inset-top,0px))]",
  "[@media(max-height:500px)]:pb-[max(0.5rem,env(safe-area-inset-bottom,0px))]",
].join(" ");

export const authCardHeaderClassName = [
  "text-center space-y-4",
  "[@media(max-height:500px)]:space-y-1",
  "[@media(max-height:500px)]:gap-1",
  "[@media(max-height:500px)]:pt-2",
].join(" ");

export const authCardContentClassName = [
  "space-y-4",
  "[@media(max-height:500px)]:space-y-2",
  "[@media(max-height:500px)]:py-3",
].join(" ");

export const authCardTitleClassName = "text-2xl [@media(max-height:500px)]:text-xl";

export function AuthScreen({ children }: { children: ReactNode }) {
  return (
    <div data-auth-screen className={authScreenClassName}>
      <div className="m-auto w-full max-w-md">{children}</div>
    </div>
  );
}

export function AuthLogo() {
  return (
    <div data-auth-logo className="flex justify-center [@media(max-height:500px)]:hidden">
      <Logo className="h-12 w-auto" />
    </div>
  );
}
