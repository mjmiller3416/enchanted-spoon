import { QuantityInput } from "enchanted-spoon";

const noop = () => {};

export const IngredientRow = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-md">
    <div className="flex items-center gap-3">
      <QuantityInput value={1.5} onChange={noop} className="w-16" />
      <span className="text-sm text-muted-foreground">cups</span>
      <span className="text-sm">all-purpose flour</span>
    </div>
    <div className="flex items-center gap-3">
      <QuantityInput value={0.5} onChange={noop} className="w-16" />
      <span className="text-sm text-muted-foreground">tsp</span>
      <span className="text-sm">red pepper flakes</span>
    </div>
    <div className="flex items-center gap-3">
      <QuantityInput value={2} onChange={noop} className="w-16" />
      <span className="text-sm text-muted-foreground">lbs</span>
      <span className="text-sm">chicken thighs</span>
    </div>
  </div>
);

export const FractionFormatting = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-3">
    <QuantityInput value={0.25} onChange={noop} className="w-16" />
    <QuantityInput value={0.5} onChange={noop} className="w-16" />
    <QuantityInput value={0.75} onChange={noop} className="w-16" />
    <QuantityInput value={1.5} onChange={noop} className="w-16" />
    <QuantityInput value={3} onChange={noop} className="w-16" />
  </div>
);

export const EmptyAndError = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-sm">
    <QuantityInput value={null} onChange={noop} className="w-24" />
    <div className="space-y-2">
      <QuantityInput value={null} onChange={noop} className="w-24 border-destructive" />
      <p className="text-xs text-destructive">Enter a quantity like 1 1/2</p>
    </div>
  </div>
);
