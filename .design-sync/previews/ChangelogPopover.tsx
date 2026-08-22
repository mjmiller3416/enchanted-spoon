import * as React from "react";
import { ChangelogPopover } from "enchanted-spoon";

const noop = () => {};

// Closed state: the TopNav bell trigger with the unread pulse dot. (On the
// white sheet canvas the ghost button is invisible without the dark wrapper.)
export const BellTrigger = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-center justify-center">
    <ChangelogPopover
      newItemCount={3}
      hasNewUpdates
      onOpen={noop}
      onViewAll={noop}
      onViewItem={noop}
    />
  </div>
);

// Open state: the popover's open flag is internal component state, so the
// preview clicks the trigger on mount to reveal the "What's New" panel
// (real changelog entries from data/changelog).
export const OpenPanel = () => {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    ref.current?.querySelector("button")?.click();
  }, []);
  return (
    <div
      ref={ref}
      className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl min-h-40 flex justify-end"
    >
      <ChangelogPopover
        newItemCount={2}
        hasNewUpdates
        onOpen={noop}
        onViewAll={noop}
        onViewItem={noop}
      />
    </div>
  );
};
