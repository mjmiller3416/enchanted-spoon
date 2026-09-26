import { SectionHeader } from "enchanted-spoon";
import { Palette, Sparkles } from "lucide-react";

// Settings/admin section heading — icon tile + title + one-line description.
export const Primary = () => (
  <div className="bg-background text-foreground p-6 rounded-xl max-w-2xl">
    <SectionHeader
      icon={Palette}
      title="Appearance"
      description="Choose a theme and how dense recipe cards look."
    />
  </div>
);

export const Secondary = () => (
  <div className="bg-background text-foreground p-6 rounded-xl max-w-2xl">
    <SectionHeader
      icon={Sparkles}
      title="AI Features"
      description="Control cooking tips, meal suggestions, and image generation."
      accentColor="secondary"
    />
  </div>
);
