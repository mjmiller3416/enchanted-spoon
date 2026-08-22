import { Textarea, Label } from "enchanted-spoon";

const stack = "bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-md";

export const Default = () => (
  <div className={stack}>
    <div className="space-y-2">
      <Label htmlFor="direction-step">Direction — Step 1</Label>
      <Textarea
        id="direction-step"
        defaultValue="Sear the chicken thighs skin-side down in a hot cast-iron skillet for 6 minutes, until the skin is golden and crisp."
      />
    </div>
    <div className="space-y-2">
      <Label htmlFor="meal-notes">Meal Notes</Label>
      <Textarea id="meal-notes" placeholder="Add prep notes, substitutions, or serving ideas…" />
    </div>
  </div>
);

export const Sizes = () => (
  <div className={stack}>
    <Textarea size="sm" placeholder="Small — quick note about this meal" />
    <Textarea size="default" placeholder="Default — describe this recipe" />
    <Textarea size="lg" placeholder="Large — paste full directions to import" />
  </div>
);

export const Disabled = () => (
  <div className={stack}>
    <Textarea
      disabled
      defaultValue="Simmer the marinara with fresh basil for 20 minutes while the pasta cooks."
    />
  </div>
);
