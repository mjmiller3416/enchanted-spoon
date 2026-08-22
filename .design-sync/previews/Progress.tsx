import { Progress } from "enchanted-spoon";

const stack = "bg-background text-foreground p-6 rounded-xl flex flex-col gap-4 max-w-md";

export const WizardProgress = () => (
  <div className={stack}>
    <div className="flex items-center justify-between text-sm">
      <span className="font-medium">Add Recipe — Ingredients</span>
      <span className="text-muted-foreground">Step 3 of 5</span>
    </div>
    <Progress value={60} className="h-1" />
  </div>
);

export const ValueSweep = () => (
  <div className={stack}>
    <p className="text-sm text-muted-foreground">Import queued</p>
    <Progress value={0} />
    <p className="text-sm text-muted-foreground">Parsing ingredients — 25%</p>
    <Progress value={25} />
    <p className="text-sm text-muted-foreground">Estimating nutrition — 50%</p>
    <Progress value={50} />
    <p className="text-sm text-muted-foreground">Generating image — 75%</p>
    <Progress value={75} />
    <p className="text-sm text-muted-foreground">Recipe imported — 100%</p>
    <Progress value={100} />
  </div>
);

export const WeeklyGoal = () => (
  <div className={stack}>
    <div className="flex items-center justify-between text-sm">
      <span className="font-medium">Meals planned this week</span>
      <span className="text-muted-foreground">9 of 15</span>
    </div>
    <Progress value={60} className="h-3" />
  </div>
);
