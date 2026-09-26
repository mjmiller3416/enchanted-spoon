import { TourStepCard } from "enchanted-spoon";
import { CalendarDays, Search, Sparkles } from "lucide-react";

// One step of the guided tour. Normally floated by TourSpotlight; shown
// standalone here.
export const FirstStep = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-96">
    <TourStepCard
      title="Find any recipe fast"
      description="Search by name or ingredient, then narrow things down with the quick filters."
      icon={Search}
      stepNumber={1}
      stepCount={11}
      onNext={() => {}}
      onSkip={() => {}}
    />
  </div>
);

export const MiddleStep = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-96">
    <TourStepCard
      title="Ask Genie"
      description="Genie can suggest meals from what you have on hand, write new recipes, and answer cooking questions."
      icon={Sparkles}
      stepNumber={6}
      stepCount={11}
      onNext={() => {}}
      onBack={() => {}}
      onSkip={() => {}}
    />
  </div>
);

export const LastStepPending = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-96">
    <TourStepCard
      title="Plan your week"
      description="Add meals to the planner and their ingredients flow straight into your shopping list."
      icon={CalendarDays}
      stepNumber={11}
      stepCount={11}
      onNext={() => {}}
      onBack={() => {}}
      onSkip={() => {}}
      isPending
    />
  </div>
);
