import type { Metadata } from "next";
import { Suspense } from "react";
import { SidebarPageSkeleton } from "@/components/layout/SidebarPageSkeleton";
import { SettingsView } from "./_components";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  // Suspense boundary required: SettingsView reads useSearchParams()
  // for the Stripe Checkout return params.
  return (
    <Suspense fallback={<SidebarPageSkeleton />}>
      <SettingsView />
    </Suspense>
  );
}
