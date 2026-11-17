import type { ComponentProps } from "react";
import { DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/** Shared framing for recipe and meal editors: full screen on phones and
 * short landscape, inset on tablet and desktop. Width lives in the
 * `editor-dialog` utility so it isn't undone by DialogContent's w-full. */
export function EditorDialogContent({ className, ...props }: ComponentProps<typeof DialogContent>) {
  return <DialogContent {...props} size="xl" className={cn("editor-dialog flex gap-0 rounded-none p-0", className)} />;
}
