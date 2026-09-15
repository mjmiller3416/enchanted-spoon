"use client";

import { useAssistantDialog } from "@/lib/providers/AssistantProvider";
import { useRef, useState } from "react";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useMediaQuery } from "@/hooks/ui/useMediaQuery";
import { cn } from "@/lib/utils";
import { AssistantChatContent } from "./AssistantChatContent";

interface AssistantPopupProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AssistantPopup({ open, onOpenChange }: AssistantPopupProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const { restoreFocus } = useAssistantDialog();
  const isMobile = useMediaQuery("(max-width: 767px)");
  const [expanded, setExpanded] = useState(false);
  const modal = isMobile || expanded;
  const close = () => { setExpanded(false); onOpenChange(false); };
  return (
    <Dialog open={open} onOpenChange={value => value ? onOpenChange(true) : close()} modal={modal}>
      <DialogContent
        ref={contentRef}
        showCloseButton={false}
        className={cn("assistant-dialog flex flex-col gap-0 overflow-hidden p-0 bg-elevated", isMobile
          ? "inset-0 max-w-full translate-x-0 translate-y-0 rounded-none h-dvh w-full"
          : expanded ? "w-full max-w-2xl sm:max-w-2xl h-160" : "left-auto top-auto bottom-6 right-6 w-96 max-w-sm translate-x-0 translate-y-0 h-128")}
        onCloseAutoFocus={event => { event.preventDefault(); restoreFocus(); }}
        onInteractOutside={event => { if (!modal) event.preventDefault(); }}
        onOpenAutoFocus={event => { if (isMobile) { event.preventDefault(); contentRef.current?.focus(); } }}
        onEscapeKeyDown={event => { if (expanded && !isMobile) { event.preventDefault(); setExpanded(false); } }}
      >
        <DialogTitle className="sr-only">Genie assistant</DialogTitle>
        <DialogDescription className="sr-only">Ask for cooking help or generate a recipe draft to review.</DialogDescription>
        <div className="min-h-0 flex-1">
          <AssistantChatContent onClose={close} isMobile={isMobile} isExpanded={expanded} onExpand={() => setExpanded(true)} onCollapse={() => setExpanded(false)} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
