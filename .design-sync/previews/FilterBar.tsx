import { FilterBar, FilterPillGroup } from "enchanted-spoon";

const noop = () => {};

const MEAL_TYPES = [
  { id: "breakfast", label: "Breakfast" },
  { id: "lunch", label: "Lunch" },
  { id: "dinner", label: "Dinner" },
  { id: "snack", label: "Snack" },
];

const CATEGORIES = [
  { id: "italian", label: "Italian" },
  { id: "mexican", label: "Mexican" },
  { id: "asian", label: "Asian" },
  { id: "seafood", label: "Seafood" },
  { id: "comfort", label: "Comfort Food" },
  { id: "vegetarian", label: "Vegetarian" },
];

// Default pills with one active filter.
export const MealTypes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl">
    <FilterBar options={MEAL_TYPES} activeIds={["dinner"]} onToggle={noop} />
  </div>
);

// Longer option set wraps; multiple filters active. Uses the FilterPillGroup
// alias export.
export const Categories = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl">
    <FilterPillGroup
      options={CATEGORIES}
      activeIds={["italian", "vegetarian"]}
      onToggle={noop}
    />
  </div>
);

// Glass variant, centered — used floating over recipe imagery.
export const Glass = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl">
    <div className="bg-elevated rounded-lg p-4">
      <FilterBar
        options={MEAL_TYPES}
        activeIds={["lunch"]}
        onToggle={noop}
        variant="glass"
        align="center"
      />
    </div>
  </div>
);
