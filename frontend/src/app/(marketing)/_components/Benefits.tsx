import { BookOpen, CalendarDays, Flame, ShoppingCart, type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Reveal } from "./Reveal";

interface Benefit {
  icon: LucideIcon;
  title: string;
  body: string;
}

const BENEFITS: Benefit[] = [
  {
    icon: BookOpen,
    title: "Recipes you can change",
    body: "Create, save, and edit the dishes you cook. Favorite them and group them so Tuesday’s pasta is easy to find again.",
  },
  {
    icon: CalendarDays,
    title: "A menu for the week",
    body: "Line up mains and sides, night by night. Move a meal when the week changes.",
  },
  {
    icon: ShoppingCart,
    title: "One list for the store",
    body: "Planned meals feed the shopping list. Check items off as you go, grouped for the aisles.",
  },
  {
    icon: Flame,
    title: "A streak when you cook",
    body: "Mark a planned meal cooked and the streak keeps count of the nights you actually made dinner.",
  },
];

export function Benefits() {
  return (
    <section aria-labelledby="benefits-heading" className="border-t border-border bg-background-subtle">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-16 lg:px-6 lg:py-20">
        <div className="flex max-w-2xl flex-col gap-3">
          <h2 id="benefits-heading" className="font-display text-3xl leading-tight text-foreground sm:text-4xl">
            What you can do the first night
          </h2>
          <p className="text-muted-foreground">
            The free plan is the weekly loop: recipes, the menu, and the shopping list.
          </p>
        </div>
        <ul className="grid gap-4 sm:grid-cols-2">
          {BENEFITS.map((benefit, index) => (
            <li key={benefit.title}>
              <Reveal delay={index * 80} className="h-full">
                <Card className="h-full">
                  <CardContent className="flex flex-col gap-3">
                    <span className="flex size-10 items-center justify-center rounded-lg bg-primary-surface text-primary">
                      <benefit.icon className="size-5" strokeWidth={1.5} aria-hidden />
                    </span>
                    <h3 className="font-semibold text-foreground">{benefit.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{benefit.body}</p>
                  </CardContent>
                </Card>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
