import {
  Button,
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EditorDialogContent,
  Input,
  Label,
  Textarea,
} from "enchanted-spoon";

// Full-screen on phones, bounded 6xl panel on desktop. Children own the
// layout: header, a scrolling middle region, and a pinned footer.
export const RecipeEditor = () => (
  <Dialog open>
    <EditorDialogContent onOpenAutoFocus={(e) => e.preventDefault()}>
      <DialogHeader className="border-b border-border p-6">
        <DialogTitle>Edit Recipe</DialogTitle>
        <DialogDescription>Update the details for Bruschetta Shrimp Pasta.</DialogDescription>
      </DialogHeader>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid gap-4 max-w-2xl">
          <div className="grid gap-2">
            <Label htmlFor="recipe-name">Recipe name</Label>
            <Input id="recipe-name" defaultValue="Bruschetta Shrimp Pasta" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="recipe-notes">Notes</Label>
            <Textarea
              id="recipe-notes"
              defaultValue="Toss the tomatoes with basil and garlic 10 minutes ahead so they release their juices."
            />
          </div>
        </div>
      </div>
      <DialogFooter className="border-t border-border p-6">
        <Button variant="outline">Cancel</Button>
        <Button>Save Recipe</Button>
      </DialogFooter>
    </EditorDialogContent>
  </Dialog>
);
