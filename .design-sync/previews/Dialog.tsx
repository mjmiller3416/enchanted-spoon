import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
} from "enchanted-spoon";

// Open dialogs render in a portal over the page — card runs in "single" mode
// (cfg.overrides.Dialog) so the open state is captured inside the viewport.
export const ConfirmDelete = () => (
  <Dialog open>
    <DialogContent showCloseButton={false}>
      <DialogHeader>
        <DialogTitle>Delete this recipe?</DialogTitle>
        <DialogDescription>
          "Bruschetta Shrimp Pasta" will be removed from your library and any
          planned meals that use it. This can't be undone.
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline">Cancel</Button>
        <Button variant="destructive">Delete Recipe</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);

export const FormDialog = () => (
  <Dialog open>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>New Recipe Group</DialogTitle>
        <DialogDescription>Group related recipes into a collection.</DialogDescription>
      </DialogHeader>
      <div className="grid gap-4">
        <div className="grid gap-2">
          <Label htmlFor="group-name">Group name</Label>
          <Input id="group-name" placeholder="Weeknight Dinners" />
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline">Cancel</Button>
        <Button>Create Group</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);
