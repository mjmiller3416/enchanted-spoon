import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ScrollableCardList,
} from "enchanted-spoon";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl";

const savedMeals = [
  { name: "Bruschetta Shrimp Pasta", sides: "Garlic Butter Green Beans", tag: "Dinner" },
  { name: "Slow Cooker Beef Chili", sides: "Cornbread, Simple Slaw", tag: "Dinner" },
  { name: "Lemon Herb Roast Chicken", sides: "Smashed Potatoes", tag: "Sunday" },
  { name: "Veggie Breakfast Burritos", sides: "Fruit Salad", tag: "Breakfast" },
  { name: "Miso Glazed Salmon", sides: "Sesame Rice, Bok Choy", tag: "Dinner" },
  { name: "Caprese Grain Bowls", sides: "—", tag: "Lunch" },
];

export const SavedMealsList = () => (
  <div className={frame}>
    {/* p-4 inner padding (default) keeps card shadows from clipping at the scroll edge */}
    <ScrollableCardList className="max-h-64 max-w-md">
      <div className="space-y-2">
        {savedMeals.map((meal) => (
          <Card key={meal.name} size="sm" interactive>
            <CardHeader size="sm">
              <CardTitle className="text-sm">{meal.name}</CardTitle>
              <CardDescription>{meal.sides}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </ScrollableCardList>
  </div>
);

export const GridLayout = () => (
  <div className={frame}>
    <ScrollableCardList className="max-h-64 max-w-2xl" innerClassName="grid grid-cols-2 gap-3 p-4">
      {savedMeals.map((meal) => (
        <Card key={meal.name} size="sm">
          <CardContent size="sm">
            <div className="text-sm font-medium">{meal.name}</div>
            <div className="mt-2 flex flex-row items-center gap-2">
              <Badge variant="secondary" size="sm">
                {meal.tag}
              </Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </ScrollableCardList>
  </div>
);
