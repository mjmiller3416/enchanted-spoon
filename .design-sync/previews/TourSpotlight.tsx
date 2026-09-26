import { useLayoutEffect, useRef, useState } from "react";
import { Button, Card, CardContent, TourSpotlight, TourStepCard } from "enchanted-spoon";
import type { TourRect } from "enchanted-spoon";
import { Plus, Sparkles } from "lucide-react";

// Full-viewport overlay: dims the page, cuts out + rings the target rect, and
// floats the step card beside it. The host measures the target with
// getBoundingClientRect() — exactly what this preview does.
export const HighlightTarget = () => {
  const root = useRef<HTMLDivElement>(null);
  const target = useRef<HTMLButtonElement>(null);
  const [rect, setRect] = useState<TourRect | null>(null);
  useLayoutEffect(() => {
    // Relative to the preview root: the card frame makes it the overlay's
    // containing block. In the app, pass the viewport rect directly.
    const r = target.current?.getBoundingClientRect();
    const o = root.current?.getBoundingClientRect();
    if (r && o) setRect({ top: r.top - o.top, left: r.left - o.left, width: r.width, height: r.height });
  }, []);
  return (
    <div ref={root} className="bg-background text-foreground p-6 min-h-screen">
      <Card className="max-w-xl">
        <CardContent className="flex flex-row items-center justify-between py-6">
          <div>
            <h2 className="text-section-header">Meal Planner</h2>
            <p className="text-sm text-muted-foreground">6 of 20 planner slots in use</p>
          </div>
          <Button ref={target}>
            <Plus className="size-4" strokeWidth={1.5} />
            Add Meal
          </Button>
        </CardContent>
      </Card>
      {rect && (
        <TourSpotlight
          targetRect={rect}
          cardWidth={320}
          labelledBy="tour-title"
          describedBy="tour-desc"
          focusKey="planner-add-meal"
        >
          <TourStepCard
            title="Add a meal"
            description="Pick a main dish and up to three sides. Ingredients land on your shopping list automatically."
            icon={Plus}
            stepNumber={8}
            stepCount={11}
            onNext={() => {}}
            onBack={() => {}}
            onSkip={() => {}}
            titleId="tour-title"
            descriptionId="tour-desc"
          />
        </TourSpotlight>
      )}
    </div>
  );
};

export const Centered = () => (
  <div className="bg-background text-foreground p-6 min-h-screen">
    <TourSpotlight targetRect={null} cardWidth={320} labelledBy="tour-title-2" focusKey="genie">
      <TourStepCard
        title="Meet Genie"
        description="Your cooking assistant lives behind the sparkle button."
        icon={Sparkles}
        stepNumber={6}
        stepCount={11}
        onNext={() => {}}
        onBack={() => {}}
        onSkip={() => {}}
        titleId="tour-title-2"
      />
    </TourSpotlight>
  </div>
);
