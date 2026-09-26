"use client";
import { useCallback, useRef, useState } from "react";
import { useChatHistory } from "@/hooks/persistence/useChatHistory";
import { useAssistantChat } from "@/hooks/api/useAI";
import { classifyAiGateError } from "@/lib/paywall";
import type { RecipeGeneratedDTO } from "@/types/ai";

/** Lives with the account session, not the popup. Images remain in memory only. */
export function useAssistantSession() {
  const [input, setInput] = useState("");
  const [pendingRecipe, setPendingRecipe] = useState<{
    recipe: RecipeGeneratedDTO;
    referenceImageData: string | null;
    bannerImageData: string | null;
  } | null>(null);
  const { messages, addMessage, clearHistory } = useChatHistory();
  const chatMutation = useAssistantChat();
  const sending = useRef(false);
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || sending.current) return;
    sending.current = true;
    setInput("");
    addMessage({ role: "user", content: text });
    try {
      const response = await chatMutation.mutateAsync({ message: text, conversationHistory: messages });
      if (!response.success) throw new Error(response.error || "Failed to get response");
      if (response.recipe) setPendingRecipe({ recipe: response.recipe, referenceImageData: response.reference_image_data || null, bannerImageData: response.banner_image_data || null });
      addMessage({ role: "assistant", content: response.response || "I've created a recipe for you." });
    } catch (error) {
      addMessage({ role: "assistant", content: classifyAiGateError(error)
        ? "You've used this month's assistant allowance — see the upgrade options to keep chatting."
        : "Sorry, something went wrong. Please try again." });
    } finally { sending.current = false; }
  }, [chatMutation, messages, addMessage]);
  const clear = () => { if (!sending.current) { clearHistory(); setPendingRecipe(null); } };
  return { input, setInput, pendingRecipe, setPendingRecipe, messages, clearHistory: clear, sendMessage, isSending: chatMutation.isPending };
}
