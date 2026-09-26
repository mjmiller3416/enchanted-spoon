import { Logo } from "enchanted-spoon";

// Brand mark: fixed multi-color palette (does not tint with text color).
// The artwork is taller than wide, so size by height with w-auto.
export const Sizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-end gap-6">
    <Logo className="h-6 w-auto" />
    <Logo className="h-8 w-auto" />
    <Logo className="h-12 w-auto" />
    <Logo className="h-16 w-auto" />
  </div>
);

// TopNav lockup: mark + app name (the wordmark is composed, not a Logo prop).
export const Wordmark = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-center gap-3">
    <Logo className="h-8 w-auto" />
    <span className="text-lg font-semibold text-foreground">Enchanted Spoon</span>
  </div>
);
