// Barrel re-export — maintains backward compatibility
// All existing imports like `import { recipeApi } from "@/lib/api"` continue to work.

// Core infrastructure
export { ApiError, fetchApi, buildQueryString, API_BASE } from "./base";

// Domain API modules
export { adminApi } from "./admin";
export { billingApi } from "./billing";
export { recipeApi } from "./recipe";
export { plannerApi } from "./planner";
export { shoppingApi } from "./shopping";
export { ingredientApi } from "./ingredients";
export { uploadApi } from "./upload";
export { imageGenerationApi, cookingTipApi, mealSuggestionsApi, nutritionEstimationApi, recipeGenerationApi, recipeImportApi, AssistantApi } from "./ai";
export { dashboardApi } from "./dashboard";
export { dataManagementApi } from "./data-management";
export { feedbackApi } from "./feedback";
export { unitConversionApi } from "./units";
export { settingsApi } from "./settings";
export { recipeGroupApi } from "./recipe-groups";
export { categoryApi } from "./categories";
export { ingredientCategoryApi } from "./ingredient-categories";
export { ingredientUnitApi } from "./ingredient-units";
