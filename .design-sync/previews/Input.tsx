import { Input, Label } from "enchanted-spoon";
import { Search, Clock } from "lucide-react";

const stack = "bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-md";

export const Default = () => (
  <div className={stack}>
    <div className="space-y-2">
      <Label htmlFor="recipe-name">Recipe Name</Label>
      <Input id="recipe-name" placeholder="e.g. Creamy Tuscan Chicken" />
    </div>
    <div className="space-y-2">
      <Label htmlFor="recipe-source">Source</Label>
      <Input id="recipe-source" defaultValue="Grandma's recipe box" />
    </div>
  </div>
);

export const Sizes = () => (
  <div className={stack}>
    <Input size="sm" placeholder="Small — tag name" />
    <Input size="default" placeholder="Default — recipe name" />
    <Input size="lg" placeholder="Large — meal plan title" />
  </div>
);

export const WithIcon = () => (
  <div className={stack}>
    <Input icon={Search} placeholder="Search recipes…" />
    <Input icon={Clock} defaultValue="45" placeholder="Cook time (min)" />
  </div>
);

export const States = () => (
  <div className={stack}>
    <Input disabled placeholder="Disabled — upgrade to Pro" />
    <Input disabled defaultValue="Weeknight Dinners" />
    <div className="space-y-2">
      <Input className="border-destructive" defaultValue="" placeholder="Recipe name" />
      <p className="text-xs text-destructive">Recipe name is required</p>
    </div>
  </div>
);
