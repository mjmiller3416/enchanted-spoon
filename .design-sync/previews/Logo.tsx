import { Logo } from "recipe-app";

// Icon mark scales via className; TopNav renders it at w-8 h-8 text-primary.
export const Sizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-end gap-6">
    <Logo className="w-8 h-8 text-primary" />
    <Logo className="w-12 h-12 text-primary" />
    <Logo className="w-16 h-16 text-primary" />
    <Logo className="w-24 h-24 text-primary" />
  </div>
);

// TopNav lockup: mark + app name (the wordmark is composed, not a Logo prop).
export const Wordmark = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-center gap-3">
    <Logo className="w-8 h-8 text-primary" />
    <span className="text-lg font-semibold text-foreground">Whiskful</span>
  </div>
);

// fill="currentColor" — the mark inherits any text color token.
export const ColorVariants = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-center gap-6">
    <Logo className="w-12 h-12 text-primary" />
    <Logo className="w-12 h-12 text-foreground" />
    <Logo className="w-12 h-12 text-muted-foreground" />
  </div>
);
