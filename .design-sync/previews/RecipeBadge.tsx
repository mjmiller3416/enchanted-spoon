import { RecipeBadge, RecipeBadgeGroup } from "enchanted-spoon";

// All six badge types, composed with RecipeBadgeGroup the way the recipe
// detail header does.
export const Types = () => (
  <div className="bg-background text-foreground p-6 rounded-xl">
    <RecipeBadgeGroup>
      <RecipeBadge label="Dinner" type="mealType" />
      <RecipeBadge label="Italian" type="category" />
      <RecipeBadge label="Vegetarian" type="dietary" />
      <RecipeBadge label="Easy" type="difficulty" />
      <RecipeBadge label="AI Generated" type="ai" />
      <RecipeBadge label="Weeknight Dinners" type="group" />
    </RecipeBadgeGroup>
  </div>
);

export const Sizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-3">
    <RecipeBadge label="Breakfast" type="mealType" size="sm" />
    <RecipeBadge label="Breakfast" type="mealType" size="md" />
    <RecipeBadge label="Breakfast" type="mealType" size="lg" />
  </div>
);

// Outline variant plus the overlay variant (blur + shadow) on an elevated
// surface, as it appears floating over recipe images.
export const OutlineAndOverlay = () => (
  <div className="bg-background text-foreground p-6 rounded-xl space-y-4">
    <RecipeBadgeGroup>
      <RecipeBadge label="Mexican" type="category" variant="outline" />
      <RecipeBadge label="Lunch" type="mealType" variant="outline" />
      <RecipeBadge label="Gluten-Free" type="dietary" variant="outline" />
      <RecipeBadge label="AI Generated" type="ai" variant="outline" />
    </RecipeBadgeGroup>
    <div className="bg-elevated rounded-lg p-4">
      <RecipeBadgeGroup>
        <RecipeBadge label="Seafood" type="category" variant="overlay" />
        <RecipeBadge label="Dinner" type="mealType" variant="overlay" />
      </RecipeBadgeGroup>
    </div>
  </div>
);

// Group badge with multiple recipe groups shows the primary group plus a
// "+N" counter badge (tooltip lists the rest on hover).
export const GroupWithCount = () => (
  <div className="bg-background text-foreground p-6 rounded-xl">
    <RecipeBadgeGroup>
      <RecipeBadge
        label="Weeknight Dinners"
        type="group"
        groups={[
          { id: 1, name: "Weeknight Dinners" },
          { id: 2, name: "Family Favorites" },
          { id: 3, name: "Quick Meals" },
        ]}
      />
    </RecipeBadgeGroup>
  </div>
);
