import { NumberStepper } from "enchanted-spoon";

const grid = "bg-background text-foreground p-6 rounded-xl grid grid-cols-2 gap-4 max-w-md";

export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-sm">
    <NumberStepper label="Servings" value={4} min={1} max={99} />
  </div>
);

export const WithUnit = () => (
  <div className={grid}>
    <NumberStepper label="Prep Time" value={15} min={0} max={999} step={5} unit="min" />
    <NumberStepper label="Cook Time" value={45} min={0} max={999} step={5} unit="min" />
  </div>
);

export const AtBounds = () => (
  <div className={grid}>
    <NumberStepper label="Servings (at min)" value={1} min={1} max={99} />
    <NumberStepper label="Servings (at max)" value={99} min={1} max={99} />
  </div>
);

export const ErrorState = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-sm">
    <NumberStepper label="Cook Time" value={0} min={0} max={999} step={5} unit="min" hasError />
    <p className="text-xs text-destructive">Cook time must be greater than 0</p>
  </div>
);
