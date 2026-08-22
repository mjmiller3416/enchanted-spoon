import {
  Badge,
  Button,
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Switch,
} from "enchanted-spoon";
import { Clock, Heart, Users } from "lucide-react";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl";

export const RecipeInfoCard = () => (
  <div className={frame}>
    <Card className="max-w-sm">
      <CardHeader>
        <CardTitle>Bruschetta Shrimp Pasta</CardTitle>
        <CardDescription>
          Garlicky shrimp tossed with blistered tomatoes, basil, and linguine.
        </CardDescription>
        <CardAction>
          <Button size="icon" variant="ghost" aria-label="Favorite recipe">
            <Heart strokeWidth={1.5} />
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {/* Card itself is flex-col by default — horizontal rows need explicit flex-row */}
        <div className="flex flex-row items-center gap-4 text-sm text-muted-foreground">
          <span className="flex flex-row items-center gap-1">
            <Clock className="size-4" strokeWidth={1.5} /> 35 min
          </span>
          <span className="flex flex-row items-center gap-1">
            <Users className="size-4" strokeWidth={1.5} /> 4 servings
          </span>
        </div>
        <div className="mt-4 flex flex-row flex-wrap gap-2">
          <Badge variant="secondary">Dinner</Badge>
          <Badge variant="outline">Pescatarian</Badge>
        </div>
      </CardContent>
      <CardFooter className="border-t pb-4 justify-end gap-3">
        <Button variant="outline" size="sm">
          View Recipe
        </Button>
        <Button size="sm">Add to Planner</Button>
      </CardFooter>
    </Card>
  </div>
);

export const SettingsSectionCard = () => (
  <div className={frame}>
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Shopping List Preferences</CardTitle>
        <CardDescription>
          Control how planner meals feed your weekly shopping list.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-row items-center justify-between gap-4">
          <div>
            <div className="text-sm font-medium">Auto-add planned meals</div>
            <div className="text-sm text-muted-foreground">
              Sync ingredients when a meal joins the planner
            </div>
          </div>
          <Switch defaultChecked aria-label="Auto-add planned meals" />
        </div>
        <div className="flex flex-row items-center justify-between gap-4">
          <div>
            <div className="text-sm font-medium">Combine duplicates</div>
            <div className="text-sm text-muted-foreground">
              Merge matching ingredients across recipes
            </div>
          </div>
          <Switch aria-label="Combine duplicates" />
        </div>
      </CardContent>
    </Card>
  </div>
);

export const SizesAndInteractive = () => (
  <div className={`${frame} flex flex-wrap items-start gap-4`}>
    <Card size="sm" className="w-64">
      <CardHeader size="sm">
        <CardTitle className="text-sm">Garlic Butter Green Beans</CardTitle>
        <CardDescription>Side dish — 15 min</CardDescription>
      </CardHeader>
      <CardContent size="sm" className="text-sm text-muted-foreground">
        Small size card (size=&quot;sm&quot;)
      </CardContent>
    </Card>
    <Card interactive className="w-64">
      <CardHeader>
        <CardTitle className="text-sm">Sunday Meal Prep</CardTitle>
        <CardDescription>Interactive — hover &amp; press states</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Clickable card (interactive)
      </CardContent>
    </Card>
    <Card size="lg" className="w-80">
      <CardHeader size="lg">
        <CardTitle>Weekly Planner</CardTitle>
        <CardDescription>Large size card (size=&quot;lg&quot;)</CardDescription>
      </CardHeader>
      <CardContent size="lg" className="text-sm text-muted-foreground">
        6 of 15 planner entries used this week.
      </CardContent>
    </Card>
  </div>
);
