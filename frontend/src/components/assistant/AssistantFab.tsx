"use client";

import { usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { showsAssistantFab } from "@/components/layout/mobileChrome";
import { useAssistantDialog } from "@/lib/providers/AssistantProvider";
import { useSettings } from "@/hooks/persistence";

/**
 * Mobile-only floating "Ask the Genie" button. Desktop keeps the TopNav
 * sparkle; mobile users otherwise have to dig into the More sheet.
 * Can be turned off in Settings → AI Features (aiFeatures.showAssistantFab).
 */
export function AssistantFab() {
  const pathname = usePathname();
  const { openAssistant } = useAssistantDialog();
  const { settings, isLoaded } = useSettings();

  if (!showsAssistantFab(pathname)) return null;
  if (!isLoaded || !settings.aiFeatures.showAssistantFab) return null;

  return (
    <Button
      size="icon"
      aria-label="Ask the Genie"
      data-tour="genie-trigger"
      onClick={openAssistant}
      className="md:hidden fixed bottom-above-mobile-nav right-4 z-40 size-12 rounded-full shadow-floating print:hidden"
    >
      <Sparkles className="size-5" strokeWidth={1.5} />
    </Button>
  );
}
