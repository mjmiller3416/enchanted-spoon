import {
  Button,
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from "enchanted-spoon";
import { CalendarPlus, Copy, MoreHorizontal, Pencil, Trash2, ArrowUpDown } from "lucide-react";

// Open state — DropdownMenuContent renders inline (no portal in this DS),
// so the menu paints inside the dark frame.
export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl h-96 flex items-start">
    <DropdownMenu defaultOpen modal={false}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Recipe actions">
          <MoreHorizontal strokeWidth={1.5} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Bruschetta Shrimp Pasta</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <Pencil strokeWidth={1.5} /> Edit Recipe
        </DropdownMenuItem>
        <DropdownMenuItem>
          <CalendarPlus strokeWidth={1.5} /> Add to Meal Plan
          <DropdownMenuShortcut>⌘P</DropdownMenuShortcut>
        </DropdownMenuItem>
        <DropdownMenuItem>
          <Copy strokeWidth={1.5} /> Duplicate
        </DropdownMenuItem>
        <DropdownMenuCheckboxItem checked>Favorite</DropdownMenuCheckboxItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive">
          <Trash2 strokeWidth={1.5} /> Delete Recipe
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);

export const SortMenu = () => (
  <div className="bg-background text-foreground p-6 rounded-xl h-96 flex items-start">
    <DropdownMenu defaultOpen modal={false}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline">
          <ArrowUpDown strokeWidth={1.5} /> Sort: Newest
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Sort recipes by</DropdownMenuLabel>
        <DropdownMenuRadioGroup value="newest">
          <DropdownMenuRadioItem value="newest">Newest first</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="az">Name A to Z</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="time">Total time</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="favorites">Favorites first</DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);
