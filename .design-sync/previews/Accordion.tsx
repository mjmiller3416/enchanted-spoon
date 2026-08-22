import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "enchanted-spoon";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl";

export const RecipeFaq = () => (
  <div className={frame}>
    <Accordion type="single" collapsible defaultValue="substitute" className="max-w-md w-full">
      <AccordionItem value="substitute">
        <AccordionTrigger>Can I substitute the shrimp?</AccordionTrigger>
        <AccordionContent>
          Yes — diced chicken breast or white beans both work in Bruschetta Shrimp
          Pasta. Sear chicken 4–5 minutes per side; add beans in the last 2 minutes
          just to warm through.
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="storage">
        <AccordionTrigger>How do I store leftovers?</AccordionTrigger>
        <AccordionContent>
          Refrigerate in an airtight container for up to 3 days. Reheat gently with a
          splash of reserved pasta water so the sauce loosens without overcooking the
          shrimp.
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="sides">
        <AccordionTrigger>What sides pair well?</AccordionTrigger>
        <AccordionContent>
          Garlic Butter Green Beans, a simple arugula salad, or crusty sourdough for
          the sauce. The meal planner allows up to 3 sides per meal.
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  </div>
);

export const MultipleOpen = () => (
  <div className={frame}>
    <Accordion type="multiple" defaultValue={["prep", "cook"]} className="max-w-md w-full">
      <AccordionItem value="prep">
        <AccordionTrigger>Prep — 15 min</AccordionTrigger>
        <AccordionContent>
          Peel and devein the shrimp, halve the cherry tomatoes, mince 4 cloves of
          garlic, and chiffonade the basil.
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="cook">
        <AccordionTrigger>Cook — 20 min</AccordionTrigger>
        <AccordionContent>
          Boil the linguine while the shrimp sears in garlic butter, then blister the
          tomatoes and toss everything together off the heat.
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="serve">
        <AccordionTrigger>Serve</AccordionTrigger>
        <AccordionContent>
          Finish with basil, lemon zest, and a drizzle of good olive oil.
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  </div>
);

export const TriggerSizes = () => (
  <div className={frame}>
    <Accordion type="single" collapsible defaultValue="small" className="max-w-md w-full">
      <AccordionItem value="small">
        <AccordionTrigger size="sm">Small trigger — pantry staples</AccordionTrigger>
        <AccordionContent>Olive oil, kosher salt, black pepper, garlic.</AccordionContent>
      </AccordionItem>
      <AccordionItem value="default">
        <AccordionTrigger>Default trigger — fresh ingredients</AccordionTrigger>
        <AccordionContent>Shrimp, cherry tomatoes, basil, linguine.</AccordionContent>
      </AccordionItem>
      <AccordionItem value="large">
        <AccordionTrigger size="lg">Large trigger — equipment</AccordionTrigger>
        <AccordionContent>Large skillet, pasta pot, microplane.</AccordionContent>
      </AccordionItem>
    </Accordion>
  </div>
);
