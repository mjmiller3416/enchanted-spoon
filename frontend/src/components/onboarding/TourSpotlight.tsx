"use client";

import {
  useEffect,
  useEffectEvent,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

/** Viewport-relative rectangle (as returned by getBoundingClientRect) */
export interface TourRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface TourSpotlightProps {
  /** Rect to cut out and ring; null dims the whole page and centers the card */
  targetRect: TourRect | null;
  /** The card to float beside the target (TourStepCard / TourWelcomeCard) */
  children: ReactNode;
  /** id of the element that titles the dialog */
  labelledBy: string;
  /** id of the element that describes the dialog */
  describedBy?: string;
  /** Changing this re-runs the entrance animation and moves focus into the card */
  focusKey?: string | number;
  /** Polite live-region text, announced when it changes (e.g. "Step 2 of 9: …") */
  liveMessage?: string;
  /** Escape key */
  onEscape?: () => void;
  /** Right arrow key */
  onNext?: () => void;
  /** Left arrow key */
  onBack?: () => void;
  /** Breathing room between the target and the cutout edge, in px */
  padding?: number;
  /** Corner radius of the cutout, in px (12 matches the ring's rounded-xl) */
  radius?: number;
  /** Maximum card width, in px (shrinks to fit narrow viewports) */
  cardWidth?: number;
  className?: string;
}

const GUTTER = 16;
const GAP = 12;

// Viewport size as an external store — re-renders on resize without effects
function subscribeViewport(onChange: () => void) {
  window.addEventListener("resize", onChange);
  return () => window.removeEventListener("resize", onChange);
}
const getViewportSnapshot = () => `${window.innerWidth}x${window.innerHeight}`;
const getViewportServerSnapshot = () => "0x0";

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), Math.max(min, max));
}

/** Full-viewport rect with a rounded-rect hole; same command shape every time so it can animate */
function buildOverlayPath(vw: number, vh: number, hole: TourRect | null, radius: number) {
  const x = hole ? hole.left : vw / 2;
  const y = hole ? hole.top : vh / 2;
  const w = hole ? hole.width : 0;
  const h = hole ? hole.height : 0;
  const r = hole ? Math.min(radius, w / 2, h / 2) : 0;
  return [
    `M0 0H${vw}V${vh}H0Z`,
    `M${x + r} ${y}H${x + w - r}A${r} ${r} 0 0 1 ${x + w} ${y + r}`,
    `V${y + h - r}A${r} ${r} 0 0 1 ${x + w - r} ${y + h}`,
    `H${x + r}A${r} ${r} 0 0 1 ${x} ${y + h - r}`,
    `V${y + r}A${r} ${r} 0 0 1 ${x + r} ${y}Z`,
  ].join("");
}

function computeCardPosition(
  hole: TourRect | null,
  vw: number,
  vh: number,
  cardW: number,
  cardH: number
) {
  if (!hole) {
    return {
      top: clamp((vh - cardH) / 2, GUTTER, vh - cardH - GUTTER),
      left: (vw - cardW) / 2,
    };
  }
  const left = clamp(hole.left + hole.width / 2 - cardW / 2, GUTTER, vw - cardW - GUTTER);
  const holeBottom = hole.top + hole.height;
  const spaceBelow = vh - holeBottom - GAP - GUTTER;
  const spaceAbove = hole.top - GAP - GUTTER;
  if (spaceBelow >= cardH) return { top: holeBottom + GAP, left };
  if (spaceAbove >= cardH) return { top: hole.top - GAP - cardH, left };
  // Tall target: beside it when there is horizontal room (right first)
  const sideTop = clamp(hole.top, GUTTER, vh - cardH - GUTTER);
  const holeRight = hole.left + hole.width;
  if (vw - holeRight - GAP - GUTTER >= cardW) return { top: sideTop, left: holeRight + GAP };
  if (hole.left - GAP - GUTTER >= cardW) return { top: sideTop, left: hole.left - GAP - cardW };
  // No room anywhere: overlap on the roomier side
  return {
    top: spaceBelow >= spaceAbove ? vh - cardH - GUTTER : GUTTER,
    left,
  };
}

/**
 * TourSpotlight — full-screen modal overlay for the guided tour.
 *
 * Dims the page, cuts a rounded hole around `targetRect` with a primary ring,
 * and floats `children` (the step card) beside the target — below it when
 * there is room, otherwise above, otherwise beside, otherwise overlapping. With a null rect the
 * whole page is dimmed and the card is centered. Renders `role="dialog"`
 * with aria wiring and a polite live region, moves focus into the card when
 * `focusKey` changes (preferring `[data-tour-autofocus]`), keeps focus inside,
 * and maps Escape / arrow keys to callbacks. Props-only; honours
 * prefers-reduced-motion. Render it in a portal at the end of <body>.
 */
export function TourSpotlight({
  targetRect,
  children,
  labelledBy,
  describedBy,
  focusKey,
  liveMessage,
  onEscape,
  onNext,
  onBack,
  padding = 8,
  radius = 12,
  cardWidth = 384,
  className,
}: TourSpotlightProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const [cardHeight, setCardHeight] = useState<number | null>(null);

  const viewport = useSyncExternalStore(
    subscribeViewport,
    getViewportSnapshot,
    getViewportServerSnapshot
  );
  const [vw, vh] = viewport.split("x").map(Number);

  const hole: TourRect | null = targetRect
    ? {
        top: targetRect.top - padding,
        left: targetRect.left - padding,
        width: targetRect.width + padding * 2,
        height: targetRect.height + padding * 2,
      }
    : null;

  const cardW = Math.max(0, Math.min(cardWidth, vw - GUTTER * 2));
  const position = computeCardPosition(hole, vw, vh, cardW, cardHeight ?? 0);

  // Track the card's rendered height for placement
  useEffect(() => {
    const node = dialogRef.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => {
      setCardHeight(entry.borderBoxSize?.[0]?.blockSize ?? node.offsetHeight);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // Move focus into the card whenever the step changes
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const dialog = dialogRef.current;
      if (!dialog) return;
      const preferred = dialog.querySelector<HTMLElement>("[data-tour-autofocus]:not(:disabled)");
      (preferred ?? dialog).focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [focusKey]);

  const handleKeyDown = useEffectEvent((event: KeyboardEvent) => {
    if (event.key === "Escape" && onEscape) {
      event.preventDefault();
      event.stopPropagation();
      onEscape();
    } else if (event.key === "ArrowRight" && onNext) {
      event.preventDefault();
      onNext();
    } else if (event.key === "ArrowLeft" && onBack) {
      event.preventDefault();
      onBack();
    }
  });

  const handleFocusIn = useEffectEvent((event: FocusEvent) => {
    const root = rootRef.current;
    if (root && event.target instanceof Node && !root.contains(event.target)) {
      dialogRef.current?.focus({ preventScroll: true });
    }
  });

  // Keyboard shortcuts + keep focus inside the tour
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => handleKeyDown(event);
    const onFocus = (event: FocusEvent) => handleFocusIn(event);
    window.addEventListener("keydown", onKey, true);
    document.addEventListener("focusin", onFocus);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      document.removeEventListener("focusin", onFocus);
    };
  }, []);

  const transition = reduceMotion
    ? { duration: 0 }
    : { duration: 0.3, ease: "easeOut" as const };

  return (
    <div
      ref={rootRef}
      data-tour-root=""
      className={cn("fixed inset-0 z-50 print:hidden", className)}
      onMouseDown={(event) => {
        // Clicks on the dim layer never reach the page; keep focus in the card
        if (!dialogRef.current?.contains(event.target as Node)) {
          event.preventDefault();
        }
      }}
    >
      {vw > 0 && (
        <svg className="absolute inset-0 size-full" aria-hidden="true">
          <motion.path
            className="fill-overlay"
            fillRule="evenodd"
            initial={false}
            animate={{ d: buildOverlayPath(vw, vh, hole, radius) }}
            transition={transition}
          />
        </svg>
      )}

      {hole && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute rounded-xl border-2 border-primary shadow-glow-primary transition-all duration-300 ease-out motion-reduce:transition-none"
          style={{ top: hole.top, left: hole.left, width: hole.width, height: hole.height }}
        />
      )}

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        className={cn(
          "absolute outline-none transition-all duration-300 ease-out motion-reduce:transition-none",
          cardHeight === null && "opacity-0"
        )}
        style={{ top: position.top, left: position.left, width: cardW }}
      >
        <motion.div
          key={focusKey}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={transition}
        >
          {children}
        </motion.div>
      </div>

      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {liveMessage}
      </div>
    </div>
  );
}
