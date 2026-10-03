"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useEffectEvent,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useSettings } from "@/hooks/persistence/useSettings";
import { useCurrentUser } from "@/hooks/api";
import { WhatsNewDialog } from "@/components/common/WhatsNewDialog";
import {
  LATEST_RELEASE_ID,
  RELEASES,
  getSpotlightRelease,
  getUnreadReleaseIds,
  type SpotlightId,
} from "@/data/changelog";

/** Pre-sync, per-browser keys — read once to seed the account, then removed */
const LEGACY_LAST_SEEN_KEY = "whatsNewLastSeenRelease";
const LEGACY_SEEN_COUNT_KEY = "lastSeenChangelogCount";
/** How long a feature keeps its in-app "New" badge after release */
const SPOTLIGHT_DAYS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;

interface WhatsNewContextValue {
  /** A release newer than the account's last seen one exists */
  hasNew: boolean;
  /** Releases that were unread when this session started (for New badges) */
  unreadIds: ReadonlySet<string>;
  /** Record every release as seen */
  markSeen: () => void;
  /** Open the dialog (optionally at a release) and mark everything seen */
  openWhatsNew: (releaseId?: string | null) => void;
  /** The feature's "New" badge should show (recent, new to this account, unused) */
  isSpotlightActive: (spotlight: SpotlightId) => boolean;
  /** The user tried the feature — retire its badge on every device */
  dismissSpotlight: (spotlight: SpotlightId) => void;
}

const WhatsNewContext = createContext<WhatsNewContextValue | null>(null);

/**
 * First-visit baseline. Releases from before the account existed are history,
 * not news — but a long-time user still gets the latest release as new, so
 * the redesign introduces itself once. A legacy per-browser value wins when
 * it's further ahead.
 */
function computeBaseline(createdAt: string): string {
  const joined = createdAt.slice(0, 10);
  const lastBeforeJoining = RELEASES.find((release) => release.id.slice(0, 10) <= joined)?.id ?? "";
  const secondNewest = RELEASES[1]?.id ?? "";
  let baseline = lastBeforeJoining > secondNewest ? lastBeforeJoining : secondNewest;

  try {
    const legacy = localStorage.getItem(LEGACY_LAST_SEEN_KEY);
    if (legacy && legacy > baseline) baseline = legacy;
    localStorage.removeItem(LEGACY_LAST_SEEN_KEY);
    localStorage.removeItem(LEGACY_SEEN_COUNT_KEY);
  } catch {
    // Storage blocked — the account baseline is enough
  }
  return baseline;
}

/**
 * WhatsNewProvider — one source of truth for "What's new": which releases the
 * account has read (synced through settings), and the single dialog every
 * entry point opens (top bar, mobile More menu, Settings, Home).
 */
export function WhatsNewProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { settings, isLoaded, error, updateSettings } = useSettings();
  const { data: currentUser } = useCurrentUser();
  const { lastSeenRelease: lastSeen, dismissedSpotlights } = settings.whatsNew;
  const [mountedAt] = useState(() => Date.now());

  const [dialogOpen, setDialogOpen] = useState(false);
  const [focusReleaseId, setFocusReleaseId] = useState<string | null>(null);
  // Snapshot at session start so New badges survive marking releases seen
  const [unreadIds, setUnreadIds] = useState<ReadonlySet<string> | null>(null);
  if (unreadIds === null && isLoaded && lastSeen !== null) {
    setUnreadIds(getUnreadReleaseIds(lastSeen));
  }

  const seedBaseline = useEffectEvent((createdAt: string) => {
    updateSettings("whatsNew", { lastSeenRelease: computeBaseline(createdAt) });
  });

  // Seed once per account — only from server-confirmed settings, never from
  // a failed load, so another device's progress isn't overwritten
  const createdAt = currentUser?.created_at;
  useEffect(() => {
    if (isLoaded && !error && lastSeen === null && createdAt) seedBaseline(createdAt);
  }, [isLoaded, error, lastSeen, createdAt]);

  const hasNew = lastSeen !== null && LATEST_RELEASE_ID > lastSeen;

  const markSeen = useCallback(() => {
    if (hasNew) updateSettings("whatsNew", { lastSeenRelease: LATEST_RELEASE_ID });
  }, [hasNew, updateSettings]);

  const openWhatsNew = useCallback(
    (releaseId: string | null = null) => {
      markSeen();
      setFocusReleaseId(releaseId);
      setDialogOpen(true);
    },
    [markSeen]
  );

  const isSpotlightActive = useCallback(
    (spotlight: SpotlightId) => {
      if (!isLoaded || !createdAt || dismissedSpotlights.includes(spotlight)) return false;
      const release = getSpotlightRelease(spotlight);
      if (!release) return false;
      const releasedAt = Date.parse(`${release.id.slice(0, 10)}T00:00:00`);
      // Accounts created after the release met the feature during onboarding
      const newToAccount = Date.parse(createdAt) < releasedAt;
      return newToAccount && mountedAt - releasedAt < SPOTLIGHT_DAYS * DAY_MS;
    },
    [isLoaded, createdAt, dismissedSpotlights, mountedAt]
  );

  const dismissSpotlight = useCallback(
    (spotlight: SpotlightId) => {
      if (dismissedSpotlights.includes(spotlight)) return;
      updateSettings("whatsNew", { dismissedSpotlights: [...dismissedSpotlights, spotlight] });
    },
    [dismissedSpotlights, updateSettings]
  );

  const value = useMemo<WhatsNewContextValue>(
    () => ({
      hasNew,
      unreadIds: unreadIds ?? new Set<string>(),
      markSeen,
      openWhatsNew,
      isSpotlightActive,
      dismissSpotlight,
    }),
    [hasNew, unreadIds, markSeen, openWhatsNew, isSpotlightActive, dismissSpotlight]
  );

  return (
    <WhatsNewContext.Provider value={value}>
      {children}
      <WhatsNewDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        unreadIds={value.unreadIds}
        focusReleaseId={focusReleaseId}
        onNavigate={(href) => router.push(href)}
      />
    </WhatsNewContext.Provider>
  );
}

export function useWhatsNew(): WhatsNewContextValue {
  const value = useContext(WhatsNewContext);
  if (!value) throw new Error("useWhatsNew requires WhatsNewProvider");
  return value;
}

/**
 * useSpotlight — badge state for one feature. Inert outside the provider so
 * feature components still render on their own (previews, tests).
 */
export function useSpotlight(spotlight: SpotlightId): { active: boolean; dismiss: () => void } {
  const value = useContext(WhatsNewContext);
  const active = value?.isSpotlightActive(spotlight) ?? false;
  const dismissSpotlight = value?.dismissSpotlight;
  const dismiss = useCallback(() => {
    if (active) dismissSpotlight?.(spotlight);
  }, [active, dismissSpotlight, spotlight]);
  return { active, dismiss };
}
