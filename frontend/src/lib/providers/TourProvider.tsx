"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { BookOpen, CalendarDays, ShoppingCart } from "lucide-react";
import {
  TourSpotlight,
  TourStepCard,
  TourWelcomeCard,
  type TourRect,
} from "@/components/onboarding";
import { Logo } from "@/components/layout/Logo";
import { useOnboardingTour } from "@/hooks/persistence/useOnboardingTour";
import { useSampleDataStatus } from "@/hooks/api/useSampleData";
import { useRecipeWizardDialog } from "@/lib/providers/RecipeWizardProvider";
import { useAssistantDialog } from "@/lib/providers/AssistantProvider";
import { TOUR_STEPS } from "@/lib/tourSteps";
import { appConfig } from "@/lib/config";

// ─────────────────────────────────────────────────────────────────────────────
// Tuning
// ─────────────────────────────────────────────────────────────────────────────

/** How long a step waits for its target before falling back to a centered card */
const TARGET_TIMEOUT_MS = 4000;
const TARGET_POLL_MS = 100;
/** Let the first-run Home settle before the welcome card appears */
const AUTO_START_DELAY_MS = 800;
/** Stop looking for first-run conditions after this long on Home */
const AUTO_START_WINDOW_MS = 15000;
/** Room reserved under a target for the step card when scrolling it into view */
const CARD_ALLOWANCE_PX = 240;
/** TopNav (md+) and MobileBottomNav (<md) are both h-16 and fixed */
const NAV_HEIGHT_PX = 64;

// ─────────────────────────────────────────────────────────────────────────────
// DOM helpers
// ─────────────────────────────────────────────────────────────────────────────

function isVisible(element: HTMLElement): boolean {
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0 && getComputedStyle(element).visibility !== "hidden";
}

/** First visible element carrying any of the tokens, in token priority order */
function findTarget(tokens: string[]): HTMLElement | null {
  for (const token of tokens) {
    const nodes = document.querySelectorAll<HTMLElement>(`[data-tour~="${token}"]`);
    for (const node of Array.from(nodes)) {
      if (isVisible(node)) return node;
    }
  }
  return null;
}

function readRect(element: HTMLElement): TourRect {
  const { top, left, width, height } = element.getBoundingClientRect();
  return { top, left, width, height };
}

function sameRect(a: TourRect, b: TourRect): boolean {
  return (
    Math.abs(a.top - b.top) < 0.5 &&
    Math.abs(a.left - b.left) < 0.5 &&
    Math.abs(a.width - b.width) < 0.5 &&
    Math.abs(a.height - b.height) < 0.5
  );
}

function isFixedPosition(element: HTMLElement): boolean {
  for (let node: HTMLElement | null = element; node && node !== document.body; node = node.parentElement) {
    if (getComputedStyle(node).position === "fixed") return true;
  }
  return false;
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Scroll the window so the target (plus room for the card) sits between the fixed navs */
function bringIntoView(element: HTMLElement) {
  if (isFixedPosition(element)) return;
  const rect = element.getBoundingClientRect();
  const desktop = window.matchMedia("(min-width: 768px)").matches;
  const visibleTop = (desktop ? NAV_HEIGHT_PX : 0) + 16;
  const visibleBottom = window.innerHeight - (desktop ? 0 : NAV_HEIGHT_PX) - 16;
  const fitsAlready = rect.top >= visibleTop && rect.bottom + CARD_ALLOWANCE_PX <= visibleBottom;
  if (fitsAlready) return;

  const available = visibleBottom - visibleTop;
  const block = rect.height + CARD_ALLOWANCE_PX;
  const offset = block <= available ? visibleTop + (available - block) / 2 : visibleTop;
  window.scrollTo({
    top: window.scrollY + rect.top - offset,
    behavior: prefersReducedMotion() ? "auto" : "smooth",
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────

type TourStatus = "idle" | "welcome" | "running";

interface TourContextValue {
  /** True while the welcome card or any step is on screen */
  isActive: boolean;
  /** Replay the tour from step 1 (skips the welcome card); returns here on finish */
  startTour: () => void;
}

const TourContext = createContext<TourContextValue | null>(null);

interface TargetResolution {
  /** Which step/page/search attempt this result belongs to */
  key: string;
  /** null = timed out, show a centered card */
  element: HTMLElement | null;
}

/**
 * TourProvider — orchestrates the onboarding tour.
 *
 * Owns step state, navigates between pages for cross-page steps, waits for
 * each step's `[data-tour]` target (falling back to a centered card), keeps
 * the target scrolled into view and re-measured, makes the rest of the page
 * inert while a step is shown, and persists completion via
 * `useOnboardingTour`. Auto-starts once for brand-new accounts: only on Home,
 * only once the Get Started card (or Home with starter content) has rendered,
 * and never over the recipe wizard, the Genie, or another open dialog.
 */
export function TourProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded: authLoaded, userId } = useAuth();
  const {
    hasSeenTour,
    isLoaded: tourStoreLoaded,
    markCompleted,
    markDismissed,
  } = useOnboardingTour();
  // New accounts are seeded with starter content, so Home skips the empty-state
  // Get Started card; unseen sample data marks them as first-run instead.
  const { data: sampleData } = useSampleDataStatus(tourStoreLoaded && !hasSeenTour);
  const hasSampleData = sampleData?.has_sample_data ?? false;
  const { isOpen: wizardOpen } = useRecipeWizardDialog();
  const { isOpen: assistantOpen } = useAssistantDialog();

  const titleId = useId();
  const descriptionId = useId();

  const [status, setStatus] = useState<TourStatus>("idle");
  const [stepIndex, setStepIndex] = useState(0);
  const [returnPath, setReturnPath] = useState<string | null>(null);
  const [resolution, setResolution] = useState<TargetResolution | null>(null);
  const [measured, setMeasured] = useState<{ element: HTMLElement; rect: TourRect } | null>(null);
  const [searchNonce, setSearchNonce] = useState(0);

  const isActive = status !== "idle";
  const step = TOUR_STEPS[stepIndex];
  const stepCount = TOUR_STEPS.length;
  const onStepRoute = pathname === step.route;
  const searchKey = `${stepIndex}|${pathname}|${searchNonce}`;
  const resolved = status === "running" && onStepRoute && resolution?.key === searchKey;
  const isPending = status === "running" && !resolved;
  const targetElement = resolved ? resolution.element : null;
  const targetRect =
    targetElement && measured?.element === targetElement ? measured.rect : null;

  // ── Navigation ────────────────────────────────────────────────────────────

  const goToStep = useCallback(
    (index: number) => {
      const next = TOUR_STEPS[index];
      if (!next) return;
      setStepIndex(index);
      if (pathname !== next.route) router.push(next.route);
    },
    [pathname, router]
  );

  const close = useCallback(() => {
    setStatus("idle");
    setStepIndex(0);
    setResolution(null);
    setMeasured(null);
  }, []);

  const startTour = useCallback(() => {
    setReturnPath(pathname);
    setStatus("running");
    goToStep(0);
  }, [pathname, goToStep]);

  const beginFromWelcome = useCallback(() => {
    setStatus("running");
    goToStep(0);
  }, [goToStep]);

  const skip = useCallback(() => {
    markDismissed();
    close();
  }, [markDismissed, close]);

  const finish = useCallback(() => {
    markCompleted();
    close();
    // Land back where the tour began — for a first-run tour that's Home,
    // where the Get Started checklist picks up
    if (returnPath && returnPath !== pathname) router.push(returnPath);
  }, [markCompleted, close, returnPath, pathname, router]);

  const next = useCallback(() => {
    if (isPending) return;
    if (stepIndex >= stepCount - 1) finish();
    else goToStep(stepIndex + 1);
  }, [isPending, stepIndex, stepCount, finish, goToStep]);

  const back = useCallback(() => {
    if (isPending || stepIndex === 0) return;
    goToStep(stepIndex - 1);
  }, [isPending, stepIndex, goToStep]);

  // ── Auto-start (first run) ────────────────────────────────────────────────

  const canAutoStart =
    status === "idle" &&
    authLoaded &&
    !!userId &&
    tourStoreLoaded &&
    !hasSeenTour &&
    pathname === "/dashboard" &&
    !wizardOpen &&
    !assistantOpen;

  useEffect(() => {
    if (!canAutoStart) return;
    const startedAt = Date.now();
    let timer = 0;
    const check = () => {
      // A genuinely new user sees either the Get Started card (no recipes and
      // no plan) or Home filled with their onboarding starter content.
      const firstRunVisible =
        findTarget(["home-get-started"]) !== null ||
        (hasSampleData && findTarget(["home-overview"]) !== null);
      const dialogOpen = document.querySelector('[role="dialog"], [role="alertdialog"]') !== null;
      if (firstRunVisible && !dialogOpen) {
        setReturnPath("/dashboard");
        setStatus("welcome");
        return;
      }
      if (Date.now() - startedAt < AUTO_START_WINDOW_MS) {
        timer = window.setTimeout(check, 500);
      }
    };
    timer = window.setTimeout(check, AUTO_START_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [canAutoStart, hasSampleData]);

  // ── Stay on the step's page ───────────────────────────────────────────────
  // If the user leaves mid-step (browser back/forward), steer back once the
  // in-flight navigation has had a chance to land.
  useEffect(() => {
    if (status !== "running" || onStepRoute) return;
    const timer = window.setTimeout(() => router.push(step.route), 1500);
    return () => window.clearTimeout(timer);
  }, [status, onStepRoute, step, router]);

  // ── Target discovery ──────────────────────────────────────────────────────

  useEffect(() => {
    if (status !== "running" || !onStepRoute) return;
    const tokens = step.targets;
    const key = searchKey;
    const startedAt = Date.now();
    let timer = 0;
    const attempt = () => {
      const element = findTarget(tokens);
      if (element) {
        bringIntoView(element);
        setMeasured({ element, rect: readRect(element) });
        setResolution({ key, element });
        return;
      }
      if (Date.now() - startedAt >= TARGET_TIMEOUT_MS) {
        setResolution({ key, element: null });
        return;
      }
      timer = window.setTimeout(attempt, TARGET_POLL_MS);
    };
    // Defer one tick so a just-navigated page can commit first
    timer = window.setTimeout(attempt, 0);
    return () => window.clearTimeout(timer);
  }, [status, onStepRoute, step, searchKey]);

  // ── Target measurement (scroll / resize / layout shifts) ──────────────────

  useEffect(() => {
    if (!targetElement) return;
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        // Target unmounted or hidden (e.g. crossed a breakpoint) — search again
        if (!targetElement.isConnected || !isVisible(targetElement)) {
          setSearchNonce((n) => n + 1);
          return;
        }
        const rect = readRect(targetElement);
        setMeasured((prev) =>
          prev && prev.element === targetElement && sameRect(prev.rect, rect)
            ? prev
            : { element: targetElement, rect }
        );
      });
    };
    const resizeObserver = new ResizeObserver(measure);
    resizeObserver.observe(targetElement);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    // Catches layout shifts above the target that don't resize it
    const interval = window.setInterval(measure, 500);
    return () => {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
      window.clearInterval(interval);
    };
  }, [targetElement]);

  // ── Modal isolation: everything outside the tour is inert ─────────────────

  useEffect(() => {
    if (!isActive) return;
    const touched = new Set<Element>();
    const apply = () => {
      for (const child of Array.from(document.body.children)) {
        if (child.hasAttribute("data-tour-root") || child.hasAttribute("inert")) continue;
        child.setAttribute("inert", "");
        touched.add(child);
      }
    };
    apply();
    // Portals mounted mid-tour (toasts, tooltips) get the same treatment
    const observer = new MutationObserver(apply);
    observer.observe(document.body, { childList: true });
    return () => {
      observer.disconnect();
      touched.forEach((element) => element.removeAttribute("inert"));
    };
  }, [isActive]);

  // ── Render ────────────────────────────────────────────────────────────────

  const contextValue = useMemo(() => ({ isActive, startTour }), [isActive, startTour]);

  let overlay: ReactNode = null;
  if (status === "welcome") {
    overlay = (
      <TourSpotlight
        targetRect={null}
        labelledBy={titleId}
        describedBy={descriptionId}
        focusKey="welcome"
        onEscape={skip}
        cardWidth={448}
      >
        <TourWelcomeCard
          title={`Welcome to ${appConfig.appName}`}
          description="Take a quick tour of saving recipes, planning meals, and the shopping list that builds itself."
          media={<Logo className="h-14 w-auto" />}
          highlights={[
            { icon: BookOpen, label: "Save recipes" },
            { icon: CalendarDays, label: "Plan the week" },
            { icon: ShoppingCart, label: "Shop once" },
          ]}
          durationHint="About a minute. You can replay it anytime from Settings."
          onStart={beginFromWelcome}
          onSkip={skip}
          titleId={titleId}
          descriptionId={descriptionId}
        />
      </TourSpotlight>
    );
  } else if (status === "running") {
    const stepNumber = stepIndex + 1;
    overlay = (
      <TourSpotlight
        targetRect={isPending ? null : targetRect}
        labelledBy={titleId}
        describedBy={descriptionId}
        focusKey={isPending ? `${step.id}-pending` : step.id}
        liveMessage={
          isPending
            ? `Loading step ${stepNumber} of ${stepCount}`
            : `Step ${stepNumber} of ${stepCount}: ${step.title}`
        }
        onEscape={skip}
        onNext={isPending ? undefined : next}
        onBack={isPending || stepIndex === 0 ? undefined : back}
      >
        <TourStepCard
          title={step.title}
          description={step.description}
          icon={step.icon}
          stepNumber={stepNumber}
          stepCount={stepCount}
          onNext={next}
          onBack={back}
          onSkip={skip}
          isPending={isPending}
          titleId={titleId}
          descriptionId={descriptionId}
        />
      </TourSpotlight>
    );
  }

  return (
    <TourContext.Provider value={contextValue}>
      {children}
      {overlay && createPortal(overlay, document.body)}
    </TourContext.Provider>
  );
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error("useTour must be used within a TourProvider");
  }
  return context;
}
