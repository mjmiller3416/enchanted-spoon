"use client";

import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/Logo";
import { cn } from "@/lib/utils";
import { usePwaInstall } from "@/lib/providers/PwaInstallProvider";

const COPY = {
  home: {
    title: "Get the app",
    body: "Add it to your home screen. It opens full screen, one tap away.",
  },
  shopping: {
    title: "Shopping in the store?",
    body: "Install the app to keep your list one tap away.",
  },
} as const;

interface InstallAppBannerProps {
  context: keyof typeof COPY;
  className?: string;
}

/**
 * InstallAppBanner — proactive "install the app" nudge for phones. Renders
 * nothing unless PwaInstallProvider says now is a good moment.
 */
export function InstallAppBanner({ context, className }: InstallAppBannerProps) {
  const { showBanner, install, dismissBanner } = usePwaInstall();
  const [installing, setInstalling] = useState(false);

  if (!showBanner) return null;

  const { title, body } = COPY[context];

  const handleInstall = async () => {
    setInstalling(true);
    try {
      await install();
    } finally {
      setInstalling(false);
    }
  };

  return (
    <Card className={cn("flex-row items-center gap-3 p-4 shadow-raised", className)}>
      <Logo className="h-10 w-auto shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground">{body}</p>
      </div>
      <Button size="sm" onClick={handleInstall} disabled={installing} className="shrink-0">
        {installing && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
        Install
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={dismissBanner}
        aria-label="Not now"
        className="size-8 shrink-0 text-muted-foreground"
      >
        <X className="size-4" strokeWidth={1.5} />
      </Button>
    </Card>
  );
}
