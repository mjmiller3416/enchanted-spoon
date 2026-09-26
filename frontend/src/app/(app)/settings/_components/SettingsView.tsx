"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { RotateCcw, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/layout/PageLayout";
import { SidebarPageSkeleton } from "@/components/layout/SidebarPageSkeleton";
import { DataManagementSection } from "./sections/DataManagementSection";
import { useSettings, DEFAULT_SETTINGS } from "@/hooks/persistence/useSettings";
import { useTheme } from "@/hooks/ui";
import { currentUserQueryKeys } from "@/hooks/api/queryKeys";
import packageJson from "../../../../../package.json";
import { appConfig } from "@/lib/config";

import { CategoryNav, CATEGORIES, type SettingsCategory } from "./CategoryNav";
import { ProfileSection } from "./sections/ProfileSection";
import { BillingSection } from "./sections/BillingSection";
import { AppearanceSection } from "./sections/AppearanceSection";
import { FeedbackSection } from "./sections/FeedbackSection";
import { AIFeaturesSection } from "./sections/AIFeaturesSection";
import { RecipePreferencesSection } from "./sections/RecipePreferencesSection";
import { ShoppingListSection } from "./sections/ShoppingListSection";
import { TourReplayCard } from "./TourReplayCard";

export function SettingsView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  // Stripe Checkout returns to /settings?checkout=success|cancelled
  // (see BillingService success_url/cancel_url) — land on the billing tab.
  const requestedSection = searchParams.get("section");
  const activeCategory: SettingsCategory = searchParams.get("checkout") ? "billing" : CATEGORIES.find(category => category.id === requestedSection)?.id ?? "profile";
  const setActiveCategory = (category: SettingsCategory) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("section", category);
    params.delete("checkout");
    router.push(`/settings?${params}`, { scroll: false });
  };
  const { settings, isLoaded, updateSettings, resetSection, isSyncing, error: settingsError, retrySave } = useSettings();
  const { theme, setTheme } = useTheme();

  const checkoutHandled = useRef(false);
  useEffect(() => {
    const checkout = searchParams.get("checkout");
    if (!checkout || checkoutHandled.current) return;
    checkoutHandled.current = true;

    if (checkout === "success") {
      toast.info("Checkout completed. Refreshing your subscription status…");
      // Webhook writes the new tier — refetch profile + usage caps.
      queryClient.invalidateQueries({ queryKey: currentUserQueryKeys.all });
    } else if (checkout === "cancelled") {
      toast.info("Checkout cancelled — no changes were made.");
    }
    router.replace("/settings?section=billing", { scroll: false });
  }, [searchParams, router, queryClient]);

  // Handle reset current section
  const handleResetSection = () => {
    // Feedback, Data Management, and Billing are actions/server state,
    // not persistent local settings
    if (
      activeCategory === "feedback" ||
      activeCategory === "dataManagement" ||
      activeCategory === "billing"
    ) {
      toast.info("This section has no saved settings to reset");
      return;
    }
    // Reset the section - this auto-saves immediately
    resetSection(activeCategory);
    toast.info(
      `${CATEGORIES.find((c) => c.id === activeCategory)?.label} reset to defaults`
    );
  };

  // Render the active category content
  const renderCategoryContent = () => {
    switch (activeCategory) {
      case "profile":
        // Profile is now managed by Clerk - no props needed
        return <ProfileSection />;

      case "billing":
        return <BillingSection />;

      case "appearance":
        return <AppearanceSection theme={theme} onThemeChange={setTheme} />;

      case "recipePreferences":
        return (
          <RecipePreferencesSection
            quickFilters={settings.recipePreferences.quickFilters}
            onQuickFiltersChange={(filters) =>
              updateSettings("recipePreferences", { quickFilters: filters })
            }
          />
        );

      case "shoppingList":
        return (
          <ShoppingListSection
            categorySortOrder={settings.shoppingList.categorySortOrder}
            customCategoryOrder={settings.shoppingList.customCategoryOrder}
            onCategorySortOrderChange={(value) =>
              updateSettings("shoppingList", { categorySortOrder: value })
            }
            onCustomCategoryOrderChange={(order) =>
              updateSettings("shoppingList", { customCategoryOrder: order })
            }
          />
        );

      case "dataManagement":
        return <DataManagementSection />;

      case "aiFeatures":
        return (
          <AIFeaturesSection
            imageGenerationPrompt={settings.aiFeatures.imageGenerationPrompt}
            onPromptChange={(value) =>
              updateSettings("aiFeatures", { imageGenerationPrompt: value })
            }
            onResetPrompt={() =>
              updateSettings("aiFeatures", {
                imageGenerationPrompt:
                  DEFAULT_SETTINGS.aiFeatures.imageGenerationPrompt,
              })
            }
            showAssistantFab={settings.aiFeatures.showAssistantFab}
            onShowAssistantFabChange={(value) =>
              updateSettings("aiFeatures", { showAssistantFab: value })
            }
          />
        );

      case "feedback":
        return <FeedbackSection />;

      default:
        return null;
    }
  };

  // Show loading state (skeleton matches the final sidebar+content layout)
  if (!isLoaded) {
    return <SidebarPageSkeleton />;
  }

  return (
    <PageLayout
      title="Settings"
      description="Manage your preferences and account settings."
      actions={!["profile", "billing", "dataManagement", "feedback"].includes(activeCategory) &&
        <Button
          variant="ghost"
          onClick={handleResetSection}
          className="gap-2 text-muted-foreground hover:text-foreground"
        >
          <RotateCcw className="h-4 w-4" strokeWidth={1.5} />
          Reset Section
        </Button>
      }
    >
        <div className="mb-4 flex flex-wrap items-center gap-3 text-sm" role="status" aria-live="polite">
          {isSyncing && <Loader2 className="size-4 animate-spin text-primary" strokeWidth={1.5} />}
          <span className={settingsError ? "text-destructive" : "text-muted-foreground"}>{settingsError ?? (isSyncing ? "Saving changes…" : "All changes saved")}</span>
          {settingsError && <Button variant="outline" size="sm" disabled={isSyncing} onClick={() => void retrySave()}>Retry</Button>}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 lg:gap-8">
          {/* Left Sidebar - Category Navigation */}
          <div className="lg:col-span-1">
            <div className="sticky top-24">
              <div data-tour="settings-nav">
                <CategoryNav
                  categories={CATEGORIES}
                  activeCategory={activeCategory}
                  onCategoryChange={setActiveCategory}
                />
              </div>

              <TourReplayCard className="mt-4" />

              {/* Version Info */}
              <div className="hidden lg:block mt-4 px-4 py-3 text-center">
                <p className="text-xs text-muted-foreground">
                  {appConfig.appName} v{packageJson.version}
                </p>
                <p className="text-xs text-muted-foreground/70 mt-1">Made with ❤️</p>
              </div>
            </div>
          </div>

          {/* Right Content - Settings Form */}
          <div className="min-w-0 lg:col-span-3 space-y-6">{renderCategoryContent()}</div>
        </div>
    </PageLayout>
  );
}
