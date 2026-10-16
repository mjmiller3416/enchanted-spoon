"use client";
import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatHistory } from "@/hooks/persistence/useChatHistory";
import { useAssistantChat } from "@/hooks/api/useAI";
import { shoppingQueryKeys, useUndoShoppingAdd } from "@/hooks/api/useShopping";
import { dispatchShoppingUpdate } from "@/hooks/api/events";
import { classifyAiGateError } from "@/lib/paywall";
import type { RecipeGeneratedDTO } from "@/types/ai";
import type { ManualItemsAddResultDTO } from "@/types/shopping";

/** Lives with the account session, not the popup. Images remain in memory only. */
export function useAssistantSession() {
  const [input, setInput] = useState("");
  const [pendingRecipe, setPendingRecipe] = useState<{
    recipe: RecipeGeneratedDTO;
    referenceImageData: string | null;
    bannerImageData: string | null;
  } | null>(null);
  // Last shopping add Genie made — offered for undo until the next message
  const [shoppingUpdate, setShoppingUpdate] = useState<ManualItemsAddResultDTO | null>(null);
  const { messages, addMessage, clearHistory } = useChatHistory();
  const queryClient = useQueryClient();
  const chatMutation = useAssistantChat();
  const undoMutation = useUndoShoppingAdd();
  const sending = useRef(false);
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || sending.current) return;
    sending.current = true;
    setInput("");
    setShoppingUpdate(null);
    addMessage({ role: "user", content: text });
    try {
      const response = await chatMutation.mutateAsync({ message: text, conversationHistory: messages });
      if (!response.success) throw new Error(response.error || "Failed to get response");
      if (response.recipe) setPendingRecipe({ recipe: response.recipe, referenceImageData: response.reference_image_data || null, bannerImageData: response.banner_image_data || null });
      const update = response.shopping_update;
      if (update && update.added.length + update.reactivated.length > 0) {
        setShoppingUpdate(update);
        void queryClient.invalidateQueries({ queryKey: shoppingQueryKeys.list() });
        dispatchShoppingUpdate();
      }
      addMessage({ role: "assistant", content: response.response || "I've created a recipe for you." });
    } catch (error) {
      addMessage({ role: "assistant", content: classifyAiGateError(error)
        ? "You've used this month's assistant allowance — see the upgrade options to keep chatting."
        : "Sorry, something went wrong. Please try again." });
    } finally { sending.current = false; }
  }, [chatMutation, messages, addMessage, queryClient]);
  const undoShoppingUpdate = useCallback(async () => {
    if (!shoppingUpdate || undoMutation.isPending) return;
    try {
      await undoMutation.mutateAsync(shoppingUpdate);
      setShoppingUpdate(null);
      // Kept in history so Genie knows the add was reversed
      addMessage({ role: "assistant", content: "Undone — I took those back off your list." });
    } catch {
      // Failure toast comes from the mutation's meta.errorMessage; keep the card to retry
    }
  }, [shoppingUpdate, undoMutation, addMessage]);
  const clear = () => { if (!sending.current) { clearHistory(); setPendingRecipe(null); setShoppingUpdate(null); } };
  return {
    input, setInput, pendingRecipe, setPendingRecipe, messages, clearHistory: clear, sendMessage, isSending: chatMutation.isPending,
    shoppingUpdate, dismissShoppingUpdate: () => setShoppingUpdate(null), undoShoppingUpdate, isUndoingShoppingUpdate: undoMutation.isPending,
  };
}
