"use client";

import { useState } from "react";
import { ShoppingBag, Plus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { QuantityInput } from "@/components/forms/QuantityInput";
import { IngredientAutocomplete } from "@/components/forms/IngredientAutocomplete";
import { useAddManualItem, useUnits } from "@/hooks/api";
import { useIngredientCategoryOptions } from "@/hooks/api/useIngredientCategories";

interface QuickAddFormProps {
  variant: "compact" | "inline";
}

export function QuickAddForm({ variant }: QuickAddFormProps) {
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState<number | null>(null);
  const [unit, setUnit] = useState("");
  const [category, setCategory] = useState("");

  const addManualItem = useAddManualItem();
  const { data: units = [] } = useUnits();
  const { options: ingredientCategories } = useIngredientCategoryOptions();

  const handleAdd = () => {
    const trimmedName = itemName.trim();
    if (!trimmedName) return;

    addManualItem.mutate(
      {
        ingredient_name: trimmedName,
        quantity: quantity || 1,
        unit: unit || null,
        category: category || null,
      },
      {
        onSuccess: () => {
          setItemName("");
          setQuantity(null);
          setUnit("");
          setCategory("");
        },
      }
    );
  };

  const isDisabled = !itemName.trim() || addManualItem.isPending;

  const qtyInput = (
    <QuantityInput
      value={quantity}
      onChange={setQuantity}
      aria-label="Item quantity"
            placeholder="Qty"
      className="w-16"
    />
  );

  const unitSelect = (
    <Select value={unit} onValueChange={setUnit}>
      <SelectTrigger className={variant === "compact" ? "w-20" : "w-24"}>
        <SelectValue placeholder="Unit" />
      </SelectTrigger>
      <SelectContent>
        {units.map((u) => (
          <SelectItem key={u.value} value={u.value}>
            {u.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  const nameInput = (
    <IngredientAutocomplete
      value={itemName}
      onValueChange={setItemName}
      onCategoryChange={setCategory}
      onSubmit={() => itemName.trim() && handleAdd()}
      placeholder="Add item..."
      disabled={addManualItem.isPending}
      className={variant === "inline" ? "min-w-40" : undefined}
    />
  );

  const categorySelect = (
    <Select value={category} onValueChange={setCategory}>
      <SelectTrigger className={variant === "compact" ? "flex-1" : "w-28"}>
        <SelectValue placeholder="Category" />
      </SelectTrigger>
      <SelectContent>
        {ingredientCategories.map((cat) => (
          <SelectItem key={cat.value} value={cat.value}>
            {cat.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  const addButton = (
    <Button
      onClick={handleAdd}
      disabled={isDisabled}
      size="icon"
      aria-label="Add item to shopping list"
    >
      <Plus className="w-4 h-4" strokeWidth={1.5} />
    </Button>
  );

  if (variant === "compact") {
    return (
      <Card className="p-4 shrink-0">
        <div className="flex items-center gap-3 mb-3">
          <ShoppingBag className="h-5 w-5 text-chart-4" strokeWidth={1.5} />
          <h2 className="text-lg font-semibold text-foreground">Quick Add</h2>
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex flex-row items-center gap-2">
            {qtyInput}
            {unitSelect}
            {nameInput}
          </div>
          <div className="flex flex-row items-center gap-2">
            {categorySelect}
            {addButton}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="flex flex-row flex-wrap items-center gap-2 p-3 mb-6">
      {qtyInput}
      {unitSelect}
      {nameInput}
      {categorySelect}
      {addButton}
    </Card>
  );
}
