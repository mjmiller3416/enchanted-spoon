import {
  MultiSelect,
  MultiSelectContent,
  MultiSelectGroup,
  MultiSelectItem,
  MultiSelectTrigger,
  MultiSelectValue,
} from "enchanted-spoon";
import { useEffect, useRef, type ReactNode } from "react";

// MultiSelect owns its open state internally (no open/defaultOpen prop), so
// the open cell clicks its own trigger once on mount to pop the list.
function AutoOpen({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelector("button")?.click();
  }, []);
  return <div ref={ref}>{children}</div>;
}

const dietaryItems = (
  <MultiSelectGroup heading="Dietary">
    <MultiSelectItem value="vegan">Vegan</MultiSelectItem>
    <MultiSelectItem value="vegetarian">Vegetarian</MultiSelectItem>
    <MultiSelectItem value="gluten-free">Gluten-Free</MultiSelectItem>
    <MultiSelectItem value="dairy-free">Dairy-Free</MultiSelectItem>
    <MultiSelectItem value="keto">Keto</MultiSelectItem>
    <MultiSelectItem value="low-carb">Low-Carb</MultiSelectItem>
  </MultiSelectGroup>
);

export const Default = () => (
  <div className="bg-background text-foreground p-6 rounded-xl h-96 flex items-start">
    <AutoOpen>
      <MultiSelect defaultValues={["vegan", "gluten-free"]}>
        <MultiSelectTrigger className="w-80">
          <MultiSelectValue placeholder="Dietary preferences" />
        </MultiSelectTrigger>
        <MultiSelectContent
          search={{ placeholder: "Search preferences..." }}
        >
          {dietaryItems}
        </MultiSelectContent>
      </MultiSelect>
    </AutoOpen>
  </div>
);

export const TriggerStates = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex flex-col items-start gap-4">
    <MultiSelect>
      <MultiSelectTrigger className="w-80">
        <MultiSelectValue placeholder="Filter by meal type" />
      </MultiSelectTrigger>
      <MultiSelectContent search={false}>
        <MultiSelectItem value="breakfast">Breakfast</MultiSelectItem>
        <MultiSelectItem value="lunch">Lunch</MultiSelectItem>
        <MultiSelectItem value="dinner">Dinner</MultiSelectItem>
      </MultiSelectContent>
    </MultiSelect>
    <MultiSelect defaultValues={["gluten-free", "dairy-free", "keto"]}>
      <MultiSelectTrigger className="w-80">
        <MultiSelectValue placeholder="Dietary preferences" />
      </MultiSelectTrigger>
      <MultiSelectContent search={false}>{dietaryItems}</MultiSelectContent>
    </MultiSelect>
  </div>
);

export const SingleMode = () => (
  <div className="bg-background text-foreground p-6 rounded-xl flex items-start">
    <MultiSelect single defaultValues={["italian"]}>
      <MultiSelectTrigger className="w-72" size="sm">
        <MultiSelectValue placeholder="Category" />
      </MultiSelectTrigger>
      <MultiSelectContent search={false}>
        <MultiSelectItem value="italian">Italian</MultiSelectItem>
        <MultiSelectItem value="mexican">Mexican</MultiSelectItem>
        <MultiSelectItem value="asian">Asian</MultiSelectItem>
        <MultiSelectItem value="comfort-food">Comfort Food</MultiSelectItem>
      </MultiSelectContent>
    </MultiSelect>
  </div>
);
