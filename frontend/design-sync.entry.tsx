// Design-sync barrel — the curated component surface synced to claude.ai/design.
// Referenced by .design-sync/config.json ("entry"); bundled with esbuild into
// window.EnchantedSpoon. Not imported by the app itself.
//
// Deliberately excluded (they require the Next.js runtime and would crash in
// the design tool): RecipeCard, RecipeBrowserView, TopNav, MobileBottomNav,
// AppLayout, ConditionalAppLayout, SafeLink, FeedbackDialog,
// IngredientAutocomplete, QuickAddForm, and all assistant/ and auth/ components.

// ── ui primitives ──────────────────────────────────────────────────────────
export * from "@/components/ui/accordion";
export * from "@/components/ui/alert-dialog";
export * from "@/components/ui/avatar";
export * from "@/components/ui/badge";
export * from "@/components/ui/button";
export * from "@/components/ui/card";
export * from "@/components/ui/checkbox";
export * from "@/components/ui/collapsible";
export * from "@/components/ui/command";
export * from "@/components/ui/dialog";
export * from "@/components/ui/dropdown-menu";
export * from "@/components/ui/form";
export * from "@/components/ui/input";
export * from "@/components/ui/input-otp";
export * from "@/components/ui/label";
export * from "@/components/ui/multi-select";
export * from "@/components/ui/numeric-stepper";
export * from "@/components/ui/pagination";
export * from "@/components/ui/popover";
export * from "@/components/ui/progress";
export * from "@/components/ui/scroll-area";
export * from "@/components/ui/select";
export * from "@/components/ui/separator";
export * from "@/components/ui/sheet";
export * from "@/components/ui/skeleton";
export * from "@/components/ui/sonner";
export * from "@/components/ui/switch";
export * from "@/components/ui/tabs";
export * from "@/components/ui/textarea";
export * from "@/components/ui/toggle";
export * from "@/components/ui/toggle-group";
export * from "@/components/ui/tooltip";

// ── shared domain components ───────────────────────────────────────────────
export * from "@/components/common/ChangelogDialog";
export * from "@/components/common/ChangelogPopover";
export * from "@/components/common/CircularImage";
export * from "@/components/common/FavoriteButton";
export * from "@/components/common/FilterBar";
export * from "@/components/common/IconButton";
export * from "@/components/common/InlineGroupCreator";
export * from "@/components/common/RecipeIcon";
export * from "@/components/common/ScrollableCardList";
export * from "@/components/common/ScrollToTopButton";
export * from "@/components/common/StatCard";
export * from "@/components/forms/QuantityInput";
export * from "@/components/layout/Logo";
export * from "@/components/layout/PageHeader";
export * from "@/components/layout/PageLayout";
export * from "@/components/recipe/RecipeBadge";
export * from "@/components/recipe/RecipeBannerImage";
export * from "@/components/recipe/RecipeFilters";
export * from "@/components/recipe/RecipeImage";
