import { IconButton } from "enchanted-spoon";
import { Bell, Pencil, Printer, RefreshCw, Share2, Trash2 } from "lucide-react";

const noop = () => {};

// Recipe action row — tooltip doubles as the aria-label.
export const Actions = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-center gap-3">
    <IconButton icon={Pencil} tooltip="Edit recipe" onClick={noop} />
    <IconButton icon={Share2} tooltip="Share recipe" onClick={noop} />
    <IconButton icon={Printer} tooltip="Print recipe" onClick={noop} />
    <IconButton icon={Trash2} tooltip="Delete recipe" onClick={noop} />
  </div>
);

// Notification-dot badge variant (pulsing primary dot, top-right).
export const WithBadge = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-center gap-3">
    <IconButton icon={Bell} tooltip="What's new" badge onClick={noop} />
    <IconButton
      icon={RefreshCw}
      tooltip="Sync shopping list"
      badge
      onClick={noop}
      ariaLabel="Sync shopping list with planner"
    />
  </div>
);
