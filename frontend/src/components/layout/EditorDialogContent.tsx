import type { ComponentProps } from "react";
import { DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/** Shared framing for recipe and meal editors: full screen on phones,
 * bounded on desktop, with content owning the middle scroll region. */
export function EditorDialogContent({ className, ...props }: ComponentProps<typeof DialogContent>) {
  return <DialogContent {...props} size="xl" className={cn("editor-dialog flex max-w-full gap-0 rounded-none p-0 sm:max-w-6xl sm:rounded-xl", className)} />;
}
