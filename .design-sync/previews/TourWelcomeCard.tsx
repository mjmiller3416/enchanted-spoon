import { Logo, TourWelcomeCard } from "enchanted-spoon";
import { BookOpen, CalendarDays, ShoppingBasket } from "lucide-react";

// Intro card shown before the first tour step on a brand-new account.
export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-96">
    <TourWelcomeCard
      title="Welcome to Enchanted Spoon"
      description="Take a quick tour of where your recipes, meal plans, and shopping list live."
      media={<Logo className="h-12 w-auto" />}
      highlights={[
        { icon: BookOpen, label: "Recipes" },
        { icon: CalendarDays, label: "Meal planner" },
        { icon: ShoppingBasket, label: "Shopping list" },
      ]}
      durationHint="About 2 minutes"
      startLabel="Show me around"
      skipLabel="Maybe later"
      onStart={() => {}}
      onSkip={() => {}}
    />
  </div>
);
