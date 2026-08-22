import { Button } from "enchanted-spoon";
import { Plus, Trash2, Heart, ChevronRight, Loader2, Search } from "lucide-react";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-3";

export const Variants = () => (
  <div className={frame}>
    <Button>Add Recipe</Button>
    <Button variant="secondary">Plan Meals</Button>
    <Button variant="outline">Cancel</Button>
    <Button variant="ghost">Skip</Button>
    <Button variant="destructive">Delete</Button>
    <Button variant="dashed">
      <Plus /> Add Ingredient
    </Button>
    <Button variant="link">View all recipes</Button>
  </div>
);

export const Sizes = () => (
  <div className={frame}>
    <Button size="xs">Extra small</Button>
    <Button size="sm">Small</Button>
    <Button size="default">Default</Button>
    <Button size="lg">Large</Button>
    <Button shape="pill">Pill shape</Button>
  </div>
);

export const WithIcons = () => (
  <div className={frame}>
    <Button>
      <Plus /> New Recipe
    </Button>
    <Button variant="secondary">
      Browse <ChevronRight />
    </Button>
    <Button size="icon" aria-label="Search recipes">
      <Search />
    </Button>
    <Button size="icon-sm" variant="outline" aria-label="Favorite">
      <Heart />
    </Button>
    <Button size="icon" variant="destructive" aria-label="Delete recipe">
      <Trash2 />
    </Button>
  </div>
);

export const States = () => (
  <div className={frame}>
    <Button disabled>Disabled</Button>
    <Button disabled>
      <Loader2 className="animate-spin" /> Saving…
    </Button>
    <Button variant="outline" disabled>
      Disabled outline
    </Button>
  </div>
);
