"use client";

import { useCallback } from "react";
import { useLocalStorageState } from "./useLocalStorageState";

/**
 * Bump when the tour's steps change enough that existing users should see
 * it again. The version is baked into the storage key, so a bump reads as
 * "never seen" for everyone without a migration.
 */
export const ONBOARDING_TOUR_VERSION = 1;

const STORAGE_KEY = `enchanted-spoon-onboarding-tour-v${ONBOARDING_TOUR_VERSION}`;

export type OnboardingTourOutcome = "completed" | "dismissed";

interface OnboardingTourRecord {
  /** How the user last left the tour (null = never seen this version) */
  outcome: OnboardingTourOutcome | null;
  /** ISO timestamp of the last outcome */
  updatedAt: string | null;
}

const INITIAL_RECORD: OnboardingTourRecord = { outcome: null, updatedAt: null };

function deserializeRecord(raw: unknown): OnboardingTourRecord {
  if (!raw || typeof raw !== "object") return INITIAL_RECORD;
  const { outcome, updatedAt } = raw as Record<string, unknown>;
  return {
    outcome: outcome === "completed" || outcome === "dismissed" ? outcome : null,
    updatedAt: typeof updatedAt === "string" ? updatedAt : null,
  };
}

export interface OnboardingTourState {
  /** Tour finished or dismissed for the current tour version */
  hasSeenTour: boolean;
  outcome: OnboardingTourOutcome | null;
  markCompleted: () => void;
  markDismissed: () => void;
  /** Forget the outcome so the tour auto-starts again (dev/debug helper) */
  reset: () => void;
  /** False until the stored value has been read (gate auto-start on this) */
  isLoaded: boolean;
}

/**
 * Persisted, account-scoped onboarding-tour flags. Mirrors
 * `useGetStartedComplete`: a single versioned localStorage key through
 * `useLocalStorageState`, so it syncs across tabs and per signed-in user.
 */
export function useOnboardingTour(): OnboardingTourState {
  const [record, setRecord, isLoaded] = useLocalStorageState<OnboardingTourRecord>(
    STORAGE_KEY,
    INITIAL_RECORD,
    { deserialize: deserializeRecord }
  );

  const markCompleted = useCallback(
    () => setRecord({ outcome: "completed", updatedAt: new Date().toISOString() }),
    [setRecord]
  );
  const markDismissed = useCallback(
    () => setRecord({ outcome: "dismissed", updatedAt: new Date().toISOString() }),
    [setRecord]
  );
  const reset = useCallback(() => setRecord(INITIAL_RECORD), [setRecord]);

  return {
    hasSeenTour: record.outcome !== null,
    outcome: record.outcome,
    markCompleted,
    markDismissed,
    reset,
    isLoaded,
  };
}
