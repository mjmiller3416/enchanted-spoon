import { QueryError } from "enchanted-spoon";

// Error card shown in place of a section whose data query failed.
export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl max-w-2xl">
    <QueryError onRetry={() => {}} />
  </div>
);

export const CustomMessage = () => (
  <div className="bg-background text-foreground p-6 rounded-xl max-w-2xl">
    <QueryError
      title="Couldn't load your meal plan"
      message="Your planned meals are still saved. Check your connection and try again."
      onRetry={() => {}}
    />
  </div>
);

export const Retrying = () => (
  <div className="bg-background text-foreground p-6 rounded-xl max-w-2xl">
    <QueryError title="Couldn't load recent recipes" onRetry={() => {}} retrying />
  </div>
);
