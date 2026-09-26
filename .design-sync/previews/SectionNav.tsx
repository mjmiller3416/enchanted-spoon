import { SectionNav } from "enchanted-spoon";
import { CreditCard, Database, Palette, Sparkles, User } from "lucide-react";

// Settings sidebar. Renders a Card of ghost buttons at lg+ and a Select below
// lg (viewport-driven; the card viewport is desktop-width).
const sections = [
  { id: "profile", label: "Profile", description: "Name and account details", icon: User },
  { id: "appearance", label: "Appearance", description: "Theme and card density", icon: Palette },
  { id: "ai", label: "AI Features", description: "Tips, suggestions, images", icon: Sparkles },
  { id: "billing", label: "Billing", description: "Plan and payment method", icon: CreditCard },
  { id: "data", label: "Data Management", description: "Import, export, reset", icon: Database },
];

export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-80">
    <SectionNav sections={sections} active="appearance" onChange={() => {}} label="Settings sections" />
  </div>
);
