import {
  Button,
  Input,
  Label,
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "enchanted-spoon";
import { NotebookPen, FolderPlus } from "lucide-react";

// PopoverContent portals to body; the trigger sits at the top of a tall dark
// frame so the open popover paints over the frame below it.
export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl h-96 flex items-start gap-3">
    <Popover defaultOpen>
      <PopoverTrigger asChild>
        <Button variant="outline">
          <NotebookPen strokeWidth={1.5} /> Cooking notes
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start">
        <div className="space-y-2">
          <p className="text-sm font-semibold">Chef&apos;s notes</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Reserve a cup of pasta water before draining — it loosens the
            garlic butter sauce. Add the shrimp off the heat so they stay
            tender.
          </p>
        </div>
      </PopoverContent>
    </Popover>
  </div>
);

export const NewGroupForm = () => (
  <div className="bg-background text-foreground p-6 rounded-xl h-96 flex items-start gap-3">
    <Popover defaultOpen>
      <PopoverTrigger asChild>
        <Button variant="dashed">
          <FolderPlus strokeWidth={1.5} /> New Group
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" size="lg">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="popover-group-name">Group name</Label>
            <Input id="popover-group-name" placeholder="Weeknight Dinners" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm">
              Cancel
            </Button>
            <Button size="sm">Create Group</Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  </div>
);
