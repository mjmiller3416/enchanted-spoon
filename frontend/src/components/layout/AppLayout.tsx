"use client";

import { MotionConfig } from "framer-motion";
import { TopNav } from "@/components/layout/TopNav";
import { MobileBottomNav } from "@/components/layout/MobileBottomNav";
import { AssistantPopup } from "@/components/assistant/AssistantPopup";
import { AssistantFab } from "@/components/assistant/AssistantFab";
import { NavActionsProvider } from "@/lib/providers/NavActionsProvider";
import {
  AssistantProvider,
  useAssistantDialog,
} from "@/lib/providers/AssistantProvider";
import {
  RecipeWizardProvider,
  useRecipeWizardDialog,
} from "@/lib/providers/RecipeWizardProvider";
import { RecipeWizardView } from "@/app/(app)/recipes/_components/wizard/RecipeWizardView";
import { ScrollToTopButton } from "@/components/common/ScrollToTopButton";
import { PaywallDialog } from "@/components/common/PaywallDialog";

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const {
    isOpen: assistantOpen,
    setOpen: setAssistantOpen,
    openAssistant,
  } = useAssistantDialog();

  const { isOpen, setOpen, mode, editRecipeId, generatedSeed, seedKey } = useRecipeWizardDialog();

  return (
    <div className="flex flex-col min-h-screen print:block print:min-h-0">
      <TopNav onOpenAssistant={openAssistant} />
      <MobileBottomNav onOpenAssistant={openAssistant} />
      <main className="flex-1 pb-20 md:pb-0 print:pb-0">
        {children}
      </main>
      <AssistantFab />
      <AssistantPopup open={assistantOpen} onOpenChange={setAssistantOpen} />
      <RecipeWizardView
        key={
          mode === "edit"
            ? `edit-${editRecipeId}`
            : generatedSeed
              ? `gen-${seedKey}`
              : "create"
        }
        open={isOpen}
        onOpenChange={setOpen}
        mode={mode}
        recipeId={editRecipeId}
        initialGenerated={generatedSeed}
      />
      <ScrollToTopButton />
      <PaywallDialog />
    </div>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <NavActionsProvider>
        <AssistantProvider>
          <RecipeWizardProvider>
            <AppLayoutInner>{children}</AppLayoutInner>
          </RecipeWizardProvider>
        </AssistantProvider>
      </NavActionsProvider>
    </MotionConfig>
  );
}
