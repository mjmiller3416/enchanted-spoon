"use client";

import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  type ReactNode,
} from "react";

import { useAssistantSession } from "@/hooks/ui/useAssistantSession";

interface AssistantContextValue extends ReturnType<typeof useAssistantSession> {
  isOpen: boolean;
  restoreFocus: () => void;
  openAssistant: () => void;
  closeAssistant: () => void;
  setOpen: (open: boolean) => void;
}

const AssistantContext = createContext<AssistantContextValue | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const session = useAssistantSession();
  const [isOpen, setIsOpen] = useState(false);

  const opener = useRef<HTMLElement | null>(null);
  const openAssistant = useCallback(() => { opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null; setIsOpen(true); }, []);
  const restoreFocus = useCallback(() => { if (opener.current?.isConnected) opener.current.focus(); }, []);
  const closeAssistant = useCallback(() => setIsOpen(false), []);
  const setOpen = useCallback((open: boolean) => { if (open) openAssistant(); else setIsOpen(false); }, [openAssistant]);

  return (
    <AssistantContext.Provider
      value={{ ...session, restoreFocus, isOpen, openAssistant, closeAssistant, setOpen }}
    >
      {children}
    </AssistantContext.Provider>
  );
}

export function useAssistantDialog() {
  const context = useContext(AssistantContext);
  if (!context) {
    throw new Error("useAssistantDialog must be used within an AssistantProvider");
  }
  return context;
}
