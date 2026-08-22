import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "enchanted-spoon";

// Open state — SelectContent renders inline (portal off by default in this DS),
// so the dropdown paints inside the dark frame.
export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl h-96 flex items-start">
    <div className="w-64">
      <Select defaultOpen defaultValue="dinner">
        <SelectTrigger>
          <SelectValue placeholder="Select meal type" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Meal Type</SelectLabel>
            <SelectItem value="breakfast">Breakfast</SelectItem>
            <SelectItem value="lunch">Lunch</SelectItem>
            <SelectItem value="dinner">Dinner</SelectItem>
            <SelectItem value="dessert">Dessert</SelectItem>
            <SelectItem value="side">Side</SelectItem>
            <SelectItem value="snack">Snack</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  </div>
);

export const TriggerStates = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-col items-start gap-4 max-w-sm">
    <Select>
      <SelectTrigger size="sm">
        <SelectValue placeholder="Dietary preference" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="vegan">Vegan</SelectItem>
        <SelectItem value="gluten-free">Gluten-Free</SelectItem>
      </SelectContent>
    </Select>
    <Select defaultValue="italian">
      <SelectTrigger>
        <SelectValue placeholder="Category" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="italian">Italian</SelectItem>
        <SelectItem value="mexican">Mexican</SelectItem>
        <SelectItem value="asian">Asian</SelectItem>
      </SelectContent>
    </Select>
    <Select defaultValue="4">
      <SelectTrigger size="lg">
        <SelectValue placeholder="Servings" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="2">2 servings</SelectItem>
        <SelectItem value="4">4 servings</SelectItem>
        <SelectItem value="6">6 servings</SelectItem>
      </SelectContent>
    </Select>
    <Select disabled>
      <SelectTrigger>
        <SelectValue placeholder="Unit (select ingredient first)" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="cup">cup</SelectItem>
      </SelectContent>
    </Select>
  </div>
);
