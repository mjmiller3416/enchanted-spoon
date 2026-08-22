import { Checkbox, Label } from "enchanted-spoon";

const stack = "bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-md";

export const ShoppingList = () => (
  <div className={stack}>
    <div className="flex items-center gap-3">
      <Checkbox id="item-chicken" checked />
      <Label htmlFor="item-chicken">Chicken thighs (2 lbs)</Label>
    </div>
    <div className="flex items-center gap-3">
      <Checkbox id="item-basil" />
      <Label htmlFor="item-basil">Fresh basil (1 bunch)</Label>
    </div>
    <div className="flex items-center gap-3">
      <Checkbox id="item-parmesan" />
      <Label htmlFor="item-parmesan">Parmesan, grated (8 oz)</Label>
    </div>
  </div>
);

export const Sizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-4">
    <div className="flex items-center gap-2">
      <Checkbox id="size-sm" size="sm" checked />
      <Label htmlFor="size-sm">Generate reference image</Label>
    </div>
    <div className="flex items-center gap-2">
      <Checkbox id="size-default" size="default" checked />
      <Label htmlFor="size-default">Olive oil (2 tbsp)</Label>
    </div>
    <div className="flex items-center gap-2">
      <Checkbox id="size-lg" size="lg" checked />
      <Label htmlFor="size-lg">Mark as cooked</Label>
    </div>
  </div>
);

export const States = () => (
  <div className={stack}>
    <div className="flex items-center gap-3">
      <Checkbox id="st-unchecked" />
      <Label htmlFor="st-unchecked">Roma tomatoes (4)</Label>
    </div>
    <div className="flex items-center gap-3">
      <Checkbox id="st-checked" checked />
      <Label htmlFor="st-checked">Heavy cream (1 cup)</Label>
    </div>
    <div className="flex items-center gap-3">
      <Checkbox id="st-disabled" disabled />
      <Label htmlFor="st-disabled">Saffron threads (Pro only)</Label>
    </div>
    <div className="flex items-center gap-3">
      <Checkbox id="st-disabled-checked" disabled checked />
      <Label htmlFor="st-disabled-checked">Pantry staple — already have</Label>
    </div>
  </div>
);
