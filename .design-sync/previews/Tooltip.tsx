import {
  Badge,
  Button,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "enchanted-spoon";
import { Heart, Info, X } from "lucide-react";

// Tooltips portal to body and default to side="top" — triggers are centered
// in the frame so the open tooltip paints over the dark surface.
export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl min-h-40 flex items-center justify-center">
    <Tooltip defaultOpen>
      <TooltipTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Add to favorites">
          <Heart strokeWidth={1.5} />
        </Button>
      </TooltipTrigger>
      <TooltipContent>Add to favorites</TooltipContent>
    </Tooltip>
  </div>
);

export const Sizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl min-h-40 w-full flex items-center justify-around gap-8">
    <Tooltip defaultOpen>
      <TooltipTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Remove ingredient">
          <X strokeWidth={1.5} />
        </Button>
      </TooltipTrigger>
      <TooltipContent size="sm">Remove ingredient</TooltipContent>
    </Tooltip>
    <Tooltip defaultOpen>
      <TooltipTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Add to favorites">
          <Heart strokeWidth={1.5} />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">Add to favorites</TooltipContent>
    </Tooltip>
    <Tooltip defaultOpen>
      <TooltipTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Nutrition info">
          <Info strokeWidth={1.5} />
        </Button>
      </TooltipTrigger>
      <TooltipContent size="lg">Nutrition estimated with AI</TooltipContent>
    </Tooltip>
  </div>
);

export const RecipeSources = () => (
  <div className="bg-background text-foreground p-6 rounded-xl min-h-40 flex items-center justify-center">
    <Tooltip defaultOpen>
      <TooltipTrigger asChild>
        <Badge variant="secondary">3 recipes</Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" align="start">
        <p className="font-medium mb-1">Used in:</p>
        <ul className="space-y-1">
          <li className="text-muted-foreground">Bruschetta Shrimp Pasta</li>
          <li className="text-muted-foreground">Garlic Butter Chicken (x2)</li>
          <li className="text-muted-foreground">Weeknight Stir-Fry</li>
        </ul>
      </TooltipContent>
    </Tooltip>
  </div>
);
