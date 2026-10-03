"use client";

import { useSyncExternalStore, type ReactNode } from "react";
import { Compass, Share, SquarePlus, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Logo } from "@/components/layout/Logo";
import { appConfig } from "@/lib/config";
import { isIosInAppBrowser } from "@/lib/pwa";

const noopSubscribe = () => () => {};

interface IosInstallSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * IosInstallSheet — iOS has no install API, so "Install" opens these
 * Add to Home Screen steps instead. Opened by PwaInstallProvider.
 */
export function IosInstallSheet({ open, onOpenChange }: IosInstallSheetProps) {
  const inAppBrowser = useSyncExternalStore(noopSubscribe, isIosInAppBrowser, () => false);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="rounded-t-2xl pb-[env(safe-area-inset-bottom)]">
        <SheetHeader className="items-center pt-6 text-center">
          <Logo className="h-12 w-auto" />
          <SheetTitle className="text-lg">Install {appConfig.appName}</SheetTitle>
          <SheetDescription>
            Add it to your home screen. It opens full screen, just like an app.
          </SheetDescription>
        </SheetHeader>

        <ol className="flex flex-col gap-4 px-6">
          {inAppBrowser && (
            <InstallStep number={1} icon={Compass} title="Open this page in Safari">
              Tap the ••• or share menu in this app and choose{" "}
              <span className="font-medium text-foreground">Open in Safari</span>.
            </InstallStep>
          )}
          <InstallStep number={inAppBrowser ? 2 : 1} icon={Share} title="Tap the Share button">
            In Safari it&apos;s in the toolbar, or under the ••• menu.
          </InstallStep>
          <InstallStep number={inAppBrowser ? 3 : 2} icon={SquarePlus} title="Choose “Add to Home Screen”">
            You may need to scroll down the list to find it.
          </InstallStep>
          <InstallStep number={inAppBrowser ? 4 : 3} title="Tap “Add”">
            Then open {appConfig.appName} from your home screen. If it asks,
            sign in once more — the app keeps its own login.
          </InstallStep>
        </ol>

        <SheetFooter>
          <Button onClick={() => onOpenChange(false)}>Got it</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

interface InstallStepProps {
  number: number;
  title: string;
  icon?: LucideIcon;
  children: ReactNode;
}

function InstallStep({ number, title, icon: Icon, children }: InstallStepProps) {
  return (
    <li className="flex gap-4">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-sm font-semibold text-muted-foreground">
        {number}
      </div>
      <div className="flex min-w-0 flex-col gap-1 pt-1">
        <p className="flex items-center gap-2 text-sm font-medium text-foreground">
          {title}
          {Icon && <Icon className="size-4 text-primary" strokeWidth={1.5} />}
        </p>
        <p className="text-sm text-muted-foreground">{children}</p>
      </div>
    </li>
  );
}
