import { Badge, Tabs, TabsContent, TabsList, TabsTrigger } from "enchanted-spoon";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl";

export const RecipeDetailTabs = () => (
  <div className={frame}>
    <Tabs defaultValue="ingredients" className="max-w-md">
      <TabsList className="w-full">
        <TabsTrigger value="ingredients">Ingredients</TabsTrigger>
        <TabsTrigger value="directions">Directions</TabsTrigger>
        <TabsTrigger value="nutrition">Nutrition</TabsTrigger>
      </TabsList>
      <TabsContent value="ingredients">
        <div className="space-y-2 text-sm">
          <div className="flex flex-row justify-between gap-4">
            <span>Linguine</span>
            <span className="text-muted-foreground">12 oz</span>
          </div>
          <div className="flex flex-row justify-between gap-4">
            <span>Large shrimp, peeled</span>
            <span className="text-muted-foreground">1 lb</span>
          </div>
          <div className="flex flex-row justify-between gap-4">
            <span>Cherry tomatoes</span>
            <span className="text-muted-foreground">2 cups</span>
          </div>
          <div className="flex flex-row justify-between gap-4">
            <span>Fresh basil</span>
            <span className="text-muted-foreground">1/2 cup</span>
          </div>
        </div>
      </TabsContent>
      <TabsContent value="directions">
        <div className="space-y-2 text-sm text-muted-foreground">
          <div>1. Cook linguine until al dente; reserve pasta water.</div>
          <div>2. Sear shrimp in garlic butter, 2 minutes per side.</div>
          <div>3. Blister tomatoes, toss everything with basil.</div>
        </div>
      </TabsContent>
      <TabsContent value="nutrition">
        <div className="space-y-2 text-sm">
          <div className="flex flex-row justify-between gap-4">
            <span>Calories</span>
            <span className="text-muted-foreground">520 kcal</span>
          </div>
          <div className="flex flex-row justify-between gap-4">
            <span>Protein</span>
            <span className="text-muted-foreground">34 g</span>
          </div>
          <div className="flex flex-row items-center justify-between gap-4">
            <span>Source</span>
            <Badge variant="info" size="sm">
              AI Estimated
            </Badge>
          </div>
        </div>
      </TabsContent>
    </Tabs>
  </div>
);

export const Sizes = () => (
  <div className={`${frame} space-y-4`}>
    <Tabs defaultValue="create">
      <TabsList size="sm">
        <TabsTrigger size="sm" value="create">
          Create Meal
        </TabsTrigger>
        <TabsTrigger size="sm" value="saved">
          Saved Meals
        </TabsTrigger>
      </TabsList>
    </Tabs>
    <Tabs defaultValue="create">
      <TabsList>
        <TabsTrigger value="create">Create Meal</TabsTrigger>
        <TabsTrigger value="saved">Saved Meals</TabsTrigger>
      </TabsList>
    </Tabs>
    <Tabs defaultValue="create">
      <TabsList size="lg">
        <TabsTrigger size="lg" value="create">
          Create Meal
        </TabsTrigger>
        <TabsTrigger size="lg" value="saved">
          Saved Meals
        </TabsTrigger>
      </TabsList>
    </Tabs>
  </div>
);

export const FullWidthWithDisabled = () => (
  <div className={frame}>
    <Tabs defaultValue="week" className="max-w-md">
      <TabsList className="w-full">
        <TabsTrigger value="week" className="flex-1">
          This Week
        </TabsTrigger>
        <TabsTrigger value="next" className="flex-1">
          Next Week
        </TabsTrigger>
        <TabsTrigger value="history" className="flex-1" disabled>
          History
        </TabsTrigger>
      </TabsList>
      <TabsContent value="week" className="text-sm text-muted-foreground">
        6 of 15 planner entries used. Tonight: Bruschetta Shrimp Pasta with Garlic
        Butter Green Beans.
      </TabsContent>
    </Tabs>
  </div>
);
