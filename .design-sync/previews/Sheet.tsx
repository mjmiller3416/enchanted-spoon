import {
  Button,
  Checkbox,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "enchanted-spoon";
import {
  CalendarDays,
  LayoutDashboard,
  Settings,
  ShoppingCart,
  SlidersHorizontal,
  UtensilsCrossed,
} from "lucide-react";

// Sheets portal to body and pin to a viewport edge — captured full-bleed in
// single card mode. Mirrors the recipe browser's filter sidebar.
export const Default = () => (
  <Sheet open>
    <SheetContent side="right" onOpenAutoFocus={(e) => e.preventDefault()}>
      <SheetHeader>
        <SheetTitle className="flex items-center gap-2">
          <SlidersHorizontal className="size-4 text-primary" strokeWidth={1.5} />
          Filters
        </SheetTitle>
        <SheetDescription>Narrow down your recipe library.</SheetDescription>
      </SheetHeader>
      <Separator />
      <div className="flex-1 px-4 space-y-4">
        <div className="space-y-2">
          <Label>Category</Label>
          <Select defaultValue="italian">
            <SelectTrigger>
              <SelectValue placeholder="All categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="italian">Italian</SelectItem>
              <SelectItem value="mexican">Mexican</SelectItem>
              <SelectItem value="asian">Asian</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Meal type</Label>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Checkbox id="filter-dinner" defaultChecked />
              <Label htmlFor="filter-dinner" className="font-normal">
                Dinner
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="filter-lunch" />
              <Label htmlFor="filter-lunch" className="font-normal">
                Lunch
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="filter-breakfast" />
              <Label htmlFor="filter-breakfast" className="font-normal">
                Breakfast
              </Label>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox id="filter-favorites" defaultChecked />
          <Label htmlFor="filter-favorites" className="font-normal">
            Favorites only
          </Label>
        </div>
      </div>
      <SheetFooter>
        <Button>Apply Filters</Button>
        <Button variant="outline">Clear All</Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
);

export const NavigationDrawer = () => (
  <Sheet open>
    <SheetContent side="left" onOpenAutoFocus={(e) => e.preventDefault()}>
      <SheetHeader>
        <SheetTitle>Enchanted Spoon</SheetTitle>
        <SheetDescription>Plan smarter. Cook happier.</SheetDescription>
      </SheetHeader>
      <Separator />
      <div className="flex-1 px-2 space-y-1">
        <Button variant="ghost" className="w-full justify-start gap-3">
          <LayoutDashboard strokeWidth={1.5} /> Dashboard
        </Button>
        <Button variant="secondary" className="w-full justify-start gap-3">
          <UtensilsCrossed strokeWidth={1.5} /> Recipes
        </Button>
        <Button variant="ghost" className="w-full justify-start gap-3">
          <CalendarDays strokeWidth={1.5} /> Meal Planner
        </Button>
        <Button variant="ghost" className="w-full justify-start gap-3">
          <ShoppingCart strokeWidth={1.5} /> Shopping List
        </Button>
        <Button variant="ghost" className="w-full justify-start gap-3">
          <Settings strokeWidth={1.5} /> Settings
        </Button>
      </div>
    </SheetContent>
  </Sheet>
);
