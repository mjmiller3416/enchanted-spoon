import { Switch, Label } from "enchanted-spoon";

const stack = "bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-sm";

export const FilterToggles = () => (
  <div className={stack}>
    <div className="flex items-center justify-between">
      <Label htmlFor="favorites-only">Favorites Only</Label>
      <Switch id="favorites-only" checked size="sm" />
    </div>
    <div className="flex items-center justify-between">
      <Label htmlFor="quick-meals">Quick meals (under 30 min)</Label>
      <Switch id="quick-meals" size="sm" />
    </div>
  </div>
);

export const Sizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-4">
    <div className="flex items-center gap-2">
      <Switch id="sw-sm" size="sm" checked />
      <Label htmlFor="sw-sm">Small</Label>
    </div>
    <div className="flex items-center gap-2">
      <Switch id="sw-default" size="default" checked />
      <Label htmlFor="sw-default">Default</Label>
    </div>
    <div className="flex items-center gap-2">
      <Switch id="sw-lg" size="lg" checked />
      <Label htmlFor="sw-lg">Large</Label>
    </div>
  </div>
);

export const States = () => (
  <div className={stack}>
    <div className="flex items-center justify-between">
      <Label htmlFor="sw-off">Show cleared planner entries</Label>
      <Switch id="sw-off" />
    </div>
    <div className="flex items-center justify-between">
      <Label htmlFor="sw-on">Auto-add to shopping list</Label>
      <Switch id="sw-on" checked />
    </div>
    <div className="flex items-center justify-between">
      <Label htmlFor="sw-disabled-off">AI meal suggestions (Pro)</Label>
      <Switch id="sw-disabled-off" disabled />
    </div>
    <div className="flex items-center justify-between">
      <Label htmlFor="sw-disabled-on">Sync across devices</Label>
      <Switch id="sw-disabled-on" disabled checked />
    </div>
  </div>
);
