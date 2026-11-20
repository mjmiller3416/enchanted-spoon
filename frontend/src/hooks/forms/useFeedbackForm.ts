"use client";

import { useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { feedbackApi } from "@/lib/api";
import { ApiError } from "@/lib/api/base";

// ============================================================================
// CONSTANTS
// ============================================================================

export const FEEDBACK_SUPPORT_EMAIL = "info@enchantedspoon.app";

/** Shown in the feedback dialog and settings. Does not promise a public tracker. */
export const FEEDBACK_INTRO =
  "Your feedback goes straight to our team. Please don't include private or sensitive information.";

export function feedbackFailureMessage(error: unknown): string {
  const suggestion = `Please email ${FEEDBACK_SUPPORT_EMAIL}.`;
  const detail = error instanceof Error ? error.message.trim() : "";
  if (!detail) {
    return `Failed to submit feedback. ${suggestion}`;
  }
  if (detail.toLowerCase().includes(FEEDBACK_SUPPORT_EMAIL.toLowerCase())) {
    return detail;
  }
  return `${detail} ${suggestion}`;
}

export const FEEDBACK_CATEGORIES = [
  { value: "Feature Request", label: "Feature Request" },
  { value: "Bug Report", label: "Bug Report" },
  { value: "General Feedback", label: "General Feedback" },
  { value: "Question", label: "Question" },
] as const;

export type FeedbackCategory = (typeof FEEDBACK_CATEGORIES)[number]["value"];

// ============================================================================
// TYPES
// ============================================================================

export interface FeedbackMetadata {
  /** The page path where feedback was submitted from */
  page_url?: string;
  /** User agent string */
  user_agent?: string;
  /** Viewport dimensions */
  viewport?: string;
  /** Any additional context */
  [key: string]: string | undefined;
}

export interface UseFeedbackFormOptions {
  /** Optional metadata to include with the feedback (e.g., current page) */
  metadata?: FeedbackMetadata;
  /** Callback when submission succeeds */
  onSuccess?: () => void;
  /** Callback when submission fails */
  onError?: (error: Error) => void;
}

export interface UseFeedbackFormReturn {
  // State
  category: string;
  message: string;
  isSubmitting: boolean;
  canSubmit: boolean;

  // Actions
  setCategory: (category: string) => void;
  setMessage: (message: string) => void;
  handleSubmit: () => Promise<void>;
  reset: () => void;

  // Helpers
  remainingChars: number;
  categories: typeof FEEDBACK_CATEGORIES;
}

// ============================================================================
// HOOK
// ============================================================================

const MIN_MESSAGE_LENGTH = 10;

/**
 * Shared hook for feedback form logic.
 * Used by both FeedbackDialog (sidebar) and FeedbackSection (settings page).
 *
 * @example
 * // Basic usage
 * const { category, setCategory, message, setMessage, handleSubmit, canSubmit } = useFeedbackForm();
 *
 * @example
 * // With metadata (e.g., for dialog that tracks page context)
 * const pathname = usePathname();
 * const { handleSubmit } = useFeedbackForm({
 *   metadata: { page_url: pathname },
 *   onSuccess: () => setDialogOpen(false),
 * });
 */
export function useFeedbackForm(options: UseFeedbackFormOptions = {}): UseFeedbackFormReturn {
  const { getToken } = useAuth();
  const { metadata, onSuccess, onError } = options;

  // Form state
  const [category, setCategory] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Computed values
  const trimmedMessage = message.trim();
  const canSubmit = Boolean(category && trimmedMessage.length >= MIN_MESSAGE_LENGTH);
  const remainingChars = Math.max(0, MIN_MESSAGE_LENGTH - trimmedMessage.length);

  // Reset form to initial state
  const reset = useCallback(() => {
    setCategory("");
    setMessage("");
  }, []);

  // Submit feedback
  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;

    setIsSubmitting(true);
    try {
      const token = await getToken();
      if (!token) {
        throw new ApiError(
          `We couldn't confirm you're signed in. Please sign in again, or email ${FEEDBACK_SUPPORT_EMAIL}.`,
          401,
        );
      }
      const response = await feedbackApi.submit({
        category,
        message: trimmedMessage,
        metadata,
      }, token);

      if (response.success) {
        toast.success(response.message);
        reset();
        onSuccess?.();
      } else {
        const errorMessage = feedbackFailureMessage(new Error(response.message));
        toast.error(errorMessage);
        onError?.(new Error(errorMessage));
      }
    } catch (error) {
      const errorMessage = feedbackFailureMessage(error);
      toast.error(errorMessage);
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setIsSubmitting(false);
    }
  }, [canSubmit, category, trimmedMessage, metadata, reset, onSuccess, onError, getToken]);

  return {
    // State
    category,
    message,
    isSubmitting,
    canSubmit,

    // Actions
    setCategory,
    setMessage,
    handleSubmit,
    reset,

    // Helpers
    remainingChars,
    categories: FEEDBACK_CATEGORIES,
  };
}
