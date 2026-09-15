"use client";

import type React from "react";
import {
  User,
  Palette,
  ChefHat,
  ShoppingCart,
  CreditCard,
  Database,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { SectionNav } from "@/components/layout/SectionNav";

// ============================================================================
// TYPES
// ============================================================================

export type SettingsCategory =
  | "profile"
  | "billing"
  | "appearance"
  | "recipePreferences"
  | "shoppingList"
  | "dataManagement"
  | "aiFeatures"
  | "feedback";

export interface CategoryConfig {
  id: SettingsCategory;
  label: string;
  icon: React.ElementType;
  description: string;
}

// ============================================================================
// CONSTANTS
// ============================================================================

export const CATEGORIES: CategoryConfig[] = [
  {
    id: "profile",
    label: "Account & Profile",
    icon: User,
    description: "Manage your personal information",
  },
  {
    id: "billing",
    label: "Plan & Billing",
    icon: CreditCard,
    description: "Subscription and AI usage",
  },
  {
    id: "appearance",
    label: "Appearance",
    icon: Palette,
    description: "Customize the look and feel",
  },
  {
    id: "recipePreferences",
    label: "Recipe Preferences",
    icon: ChefHat,
    description: "Set your recipe browsing preferences",
  },
  {
    id: "shoppingList",
    label: "Shopping List",
    icon: ShoppingCart,
    description: "Customize shopping list behavior",
  },
  {
    id: "dataManagement",
    label: "Data Management",
    icon: Database,
    description: "Export, import, and manage your data",
  },
  {
    id: "aiFeatures",
    label: "AI Features",
    icon: Sparkles,
    description: "Configure AI image generation settings",
  },
  {
    id: "feedback",
    label: "Feedback",
    icon: MessageSquare,
    description: "Share your thoughts and suggestions",
  },
];

// ============================================================================
// COMPONENT
// ============================================================================

interface CategoryNavProps {
  categories: CategoryConfig[];
  activeCategory: SettingsCategory;
  onCategoryChange: (category: SettingsCategory) => void;
}

export function CategoryNav({
  categories,
  activeCategory,
  onCategoryChange,
}: CategoryNavProps) {
  return <SectionNav sections={categories} active={activeCategory} onChange={onCategoryChange} label="Settings section" />;
}
