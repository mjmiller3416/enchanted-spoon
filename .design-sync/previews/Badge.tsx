import { Badge } from "enchanted-spoon";
import { Clock, Flame, Leaf, Sparkles } from "lucide-react";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-3";

export const Variants = () => (
  <div className={frame}>
    <Badge>Dinner</Badge>
    <Badge variant="secondary">Side Dish</Badge>
    <Badge variant="destructive">Expired</Badge>
    <Badge variant="outline">Vegetarian</Badge>
    <Badge variant="success">Synced</Badge>
    <Badge variant="warning">High Sodium</Badge>
    <Badge variant="info">AI Estimated</Badge>
    <Badge variant="muted">Archived</Badge>
  </div>
);

export const Sizes = () => (
  <div className={frame}>
    <Badge size="sm" variant="secondary">
      Gluten-Free
    </Badge>
    <Badge size="default" variant="secondary">
      Gluten-Free
    </Badge>
    <Badge size="lg" variant="secondary">
      Gluten-Free
    </Badge>
    <Badge size="sm">Breakfast</Badge>
    <Badge size="default">Lunch</Badge>
    <Badge size="lg">Dinner</Badge>
  </div>
);

export const WithIcons = () => (
  <div className={frame}>
    <Badge variant="secondary">
      <Clock strokeWidth={1.5} /> 35 min
    </Badge>
    <Badge variant="outline">
      <Leaf strokeWidth={1.5} /> Vegan
    </Badge>
    <Badge variant="destructive">
      <Flame strokeWidth={1.5} /> Spicy
    </Badge>
    <Badge variant="info">
      <Sparkles strokeWidth={1.5} /> AI Generated
    </Badge>
  </div>
);
