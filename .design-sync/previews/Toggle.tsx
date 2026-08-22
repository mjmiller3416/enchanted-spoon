import { Toggle } from "enchanted-spoon";
import { Heart, Leaf, Flame, WheatOff } from "lucide-react";

const row = "bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-3";

export const Default = () => (
  <div className={row}>
    <Toggle aria-label="Toggle favorite" defaultPressed>
      <Heart strokeWidth={1.5} /> Favorite
    </Toggle>
    <Toggle aria-label="Toggle vegetarian filter">
      <Leaf strokeWidth={1.5} /> Vegetarian
    </Toggle>
    <Toggle aria-label="Toggle spicy filter">
      <Flame strokeWidth={1.5} /> Spicy
    </Toggle>
  </div>
);

export const Variants = () => (
  <div className={row}>
    <Toggle aria-label="Default off">Dinner</Toggle>
    <Toggle aria-label="Default on" defaultPressed>
      Lunch
    </Toggle>
    <Toggle variant="outline" aria-label="Outline off">
      Breakfast
    </Toggle>
    <Toggle variant="outline" aria-label="Outline on" defaultPressed>
      Dessert
    </Toggle>
  </div>
);

export const Sizes = () => (
  <div className={row}>
    <Toggle size="sm" variant="outline" aria-label="Small toggle" defaultPressed>
      <WheatOff strokeWidth={1.5} /> Gluten-free
    </Toggle>
    <Toggle size="default" variant="outline" aria-label="Default toggle" defaultPressed>
      <Leaf strokeWidth={1.5} /> Vegan
    </Toggle>
    <Toggle size="lg" variant="outline" aria-label="Large toggle" defaultPressed>
      <Flame strokeWidth={1.5} /> Spicy
    </Toggle>
  </div>
);

export const Disabled = () => (
  <div className={row}>
    <Toggle disabled aria-label="Disabled off">
      Keto
    </Toggle>
    <Toggle disabled defaultPressed aria-label="Disabled on">
      <Heart strokeWidth={1.5} /> Favorite
    </Toggle>
    <Toggle variant="outline" disabled aria-label="Disabled outline">
      Paleo
    </Toggle>
  </div>
);
