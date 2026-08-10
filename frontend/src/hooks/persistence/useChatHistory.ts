"use client";

import { useCallback } from "react";
import type { AssistantMessage } from "@/types/ai";
import { useLocalStorageState } from "./useLocalStorageState";

// ============================================================================
// CONSTANTS
// ============================================================================

const STORAGE_KEY = "meal-genie-chat-history";
const MAX_MESSAGES = 50;

// ============================================================================
// HOOK
// ============================================================================

interface UseChatHistoryReturn {
  /**
   * List of chat messages
   */
  messages: AssistantMessage[];
  /**
   * Whether the hook has loaded from storage
   */
  isLoaded: boolean;
  /**
   * Add a single message to the chat history
   */
  addMessage: (message: AssistantMessage) => void;
  /**
   * Clear all chat history
   */
  clearHistory: () => void;
}

/**
 * Hook for persisting Genie chat history in localStorage.
 *
 * @example
 * ```tsx
 * const { messages, addMessage, clearHistory } = useChatHistory();
 *
 * // Add a user message
 * addMessage({ role: "user", content: "What can I make with chicken?" });
 *
 * // Add an assistant response
 * addMessage({ role: "assistant", content: "Here are some ideas..." });
 * ```
 */
export function useChatHistory(): UseChatHistoryReturn {
  const [messages, setMessages, isLoaded] = useLocalStorageState<AssistantMessage[]>(
    STORAGE_KEY,
    [],
    { maxItems: MAX_MESSAGES }
  );

  const addMessage = useCallback(
    (message: AssistantMessage) => {
      setMessages((prev) => [...prev, message]);
    },
    [setMessages]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
  }, [setMessages]);

  return {
    messages,
    isLoaded,
    addMessage,
    clearHistory,
  };
}
