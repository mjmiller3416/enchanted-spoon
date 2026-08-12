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
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
  const renderButton = (category: CategoryConfig) => {
    const Icon = category.icon;
    const isActive = activeCategory === category.id;

    return (
      <Button
        key={category.id}
        variant="ghost"
        onClick={() => onCategoryChange(category.id)}
        className={cn(
          "w-full h-auto flex items-center gap-3 px-4 py-3 rounded-xl text-left justify-start transition-all duration-200",
          isActive
            ? "bg-primary text-primary-foreground shadow-md hover:bg-primary/90"
            : "text-muted-foreground hover:text-foreground hover:bg-hover"
        )}
      >
        <Icon
          className={cn(
            "size-5 flex-shrink-0",
            isActive && "text-primary-foreground"
          )}
          strokeWidth={1.5}
        />
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              "text-sm font-medium",
              isActive && "text-primary-foreground"
            )}
          >
            {category.label}
          </p>
          <p
            className={cn(
              "text-xs truncate mt-0.5",
              isActive ? "text-primary-foreground/70" : "text-muted-foreground"
            )}
          >
            {category.description}
          </p>
        </div>
      </Button>
    );
  };

  return (
    <nav className="space-y-1">
      {categories.map(renderButton)}
    </nav>
  );
}
