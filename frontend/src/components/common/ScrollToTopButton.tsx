"use client";

import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 400);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <Button
      size="icon"
      aria-label="Scroll to top"
      // Mobile: bottom-left, sharing the assistant button's offset above the nav.
      // Desktop keeps the lower-right corner (the assistant button is hidden there).
      className="fixed bottom-above-mobile-nav left-4 z-40 rounded-full shadow-lg md:bottom-8 md:left-auto md:right-8 print:hidden"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
    >
      <ArrowUp strokeWidth={1.5} className="size-5" />
    </Button>
  );
}
