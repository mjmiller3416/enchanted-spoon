// src/hooks/api/index.ts
// Barrel export for all centralized API hooks
//
// Usage:
//   import { usePlannerEntries, useRecipes, useDashboardStats } from "@/hooks/api";

// Query Keys (for advanced cache manipulation)
export * from "./queryKeys";

// Events (for cross-component communication)
export * from "./events";

// Planner Hooks
export {
  // Queries
  usePlannerEntries,
  usePlannerSummary,
  useMeal,
  useMeals,
  useSavedMeals,
  useCookingStreak,
  // Mutations
  useCreateMeal,
  useUpdateMeal,
  useAddToPlanner,
  useRemoveEntry,
  useMarkComplete,
  useMarkIncomplete,
  useToggleSaveMeal,
  useCycleShoppingMode,
  useSetShoppingMode,
  useReorderEntries,
  useClearCompleted,
  useAddSideToMeal,
  // Utilities
  useRefreshPlannerEntries,
  useRefreshCookingStreak,
  useDiscardMeal,
} from "./usePlanner";

// Recipe Hooks
export {
  // Queries
  useRecipes,
  useRecipeCards,
  useRecipe,
  useRecipeCategories,
  useRecipeMealTypes,
  // Mutations
  useCreateRecipe,
  useUpdateRecipe,
  useDeleteRecipe,
  useToggleFavorite,
  // Utilities
  useRefreshRecipes,
  usePrefetchRecipe,
} from "./useRecipes";

// Dashboard Hooks
export {
  useDashboardStats,
  useRefreshDashboardStats,
} from "./useDashboard";

// AI Hooks
export {
  // Mutations
  useMealSuggestions,
  useGenerateImage,
  useGenerateBanner,
  useAssistantChat,
} from "./useAI";

// Shopping Hooks
export {
  // Query Keys
  shoppingQueryKeys,
  // Queries
  useShoppingList,
  useShoppingNotes,
  useIngredientBreakdown,
  // Mutations
  useToggleItem,
  useToggleFlagged,
  useAddManualItem,
  useDeleteItem,
  useClearManualItems,
  useClearCompletedItems,
  useGenerateShoppingList,
  useSaveShoppingNotes,
  // Utilities
  useRefreshShoppingList,
} from "./useShopping";

// Recipe Group Hooks
export {
  // Query Keys
  recipeGroupQueryKeys,
  // Queries
  useRecipeGroups,
  useRecipeGroup,
  useRecipeGroupsForRecipe,
  // Mutations
  useCreateRecipeGroup,
  useUpdateRecipeGroup,
  useDeleteRecipeGroup,
  useAssignRecipeToGroups,
  useAddRecipeToGroup,
  useRemoveRecipeFromGroup,
} from "./useRecipeGroups";

// Category Hooks
export {
  // Query Keys
  categoryQueryKeys,
  // Queries
  useCategories,
  useCategoryOptions,
  useCategory,
  // Mutations
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useReorderCategories,
  useBulkUpdateCategories,
  useResetCategories,
} from "./useCategories";

// Ingredient Category Hooks
export {
  // Query Keys
  ingredientCategoryQueryKeys,
  // Queries
  useIngredientCategories,
  useIngredientCategoryOptions,
  useIngredientCategory,
  // Mutations
  useCreateIngredientCategory,
  useUpdateIngredientCategory,
  useDeleteIngredientCategory,
  useReorderIngredientCategories,
  useBulkUpdateIngredientCategories,
  useResetIngredientCategories,
} from "./useIngredientCategories";

// Ingredient Unit Hooks
export {
  // Query Keys
  ingredientUnitQueryKeys,
  // Queries
  useIngredientUnits,
  useIngredientUnitOptions,
  useIngredientUnit,
  // Mutations
  useCreateIngredientUnit,
  useUpdateIngredientUnit,
  useDeleteIngredientUnit,
  useReorderIngredientUnits,
  useBulkUpdateIngredientUnits,
  useResetIngredientUnits,
} from "./useIngredientUnits";

// Sample Data Hooks (onboarding starter pack)
export {
  useSampleDataStatus,
  useAddSampleData,
  useRemoveSampleData,
} from "./useSampleData";

// Unit Conversion Hooks
export { useUnits } from "./useUnits";

// Billing Hooks
export {
  useMyUsage,
  useStartCheckout,
  useOpenBillingPortal,
} from "./useBilling";

// Admin Hooks
export {
  // Current User
  useCurrentUser,
  // Usage Metrics
  useAdminUsage,
  useAdminActivity,
  // User Management
  useAdminUsers,
  useGrantPro,
  useRevokePro,
  useToggleAdmin,
  useDeleteUser,
  // Database Query
  useExecuteQuery,
} from "./useAdmin";
