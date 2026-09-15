"use client";

import { ShoppingCart } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

import { SectionHeader } from "../SectionHeader";
import { UnitConversionsSection } from "./UnitConversionsSection";
import { IngredientUnitsSection } from "./IngredientUnitsSection";
import { CategoryOrderSection } from "./CategoryOrderSection";

type CategorySortOrder = "alphabetical" | "custom";

interface ShoppingListSectionProps {
  categorySortOrder: CategorySortOrder;
  customCategoryOrder: string[];
  onCategorySortOrderChange: (value: CategorySortOrder) => void;
  onCustomCategoryOrderChange: (order: string[]) => void;
}

export function ShoppingListSection({
  categorySortOrder,
  customCategoryOrder,
  onCategorySortOrderChange,
  onCustomCategoryOrderChange,
}: ShoppingListSectionProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={ShoppingCart}
            title="Shopping List"
            description="Configure how your shopping list behaves"
            accentColor="secondary"
          />

          <div className="space-y-6">
            {/* Category Display Order */}
            <CategoryOrderSection
              categorySortOrder={categorySortOrder}
              customCategoryOrder={customCategoryOrder}
              onSortOrderChange={onCategorySortOrderChange}
              onCategoryOrderChange={onCustomCategoryOrderChange}
            />

            <Separator />

            <p className="text-sm text-muted-foreground">Checked items stay on your list until you clear them.</p>
            <Separator />

            {/* Unit Conversions */}
            <UnitConversionsSection />

            <Separator />

            {/* Ingredient Units */}
            <IngredientUnitsSection />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
