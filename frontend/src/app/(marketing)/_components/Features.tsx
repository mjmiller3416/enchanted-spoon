import { Carrot, Flame, FolderHeart, Link2, Sparkles, Users, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Reveal } from "./Reveal";

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
  pro?: boolean;
}

const FEATURES: Feature[] = [
  {
    icon: Users,
    title: "Share with your household",
    body: "Invite up to five others. Everyone sees the same recipes, the same plan, and the same grocery list.",
  },
  {
    icon: Carrot,
    title: "Shop your way",
    body: "For each meal, add every ingredient, just the produce, or nothing at all if the pantry has you covered.",
  },
  {
    icon: FolderHeart,
    title: "Favorites and collections",
    body: "Star your go-tos and group recipes into collections like “Quick lunches” or “Holiday baking.”",
  },
  {
    icon: Flame,
    title: "A cooking streak",
    body: "Mark a meal as cooked and your streak ticks up. A small nudge to skip the takeout.",
  },
  {
    icon: Link2,
    title: "Import from a link",
    body: "Paste a recipe URL and the ingredients and steps come in ready to edit. No scrolling past ads.",
    pro: true,
  },
  {
    icon: Sparkles,
    title: "Start from an idea",
    body: "Describe what you’re in the mood for, like “cozy chicken, no oven,” and get a full recipe to tweak and save.",
    pro: true,
  },
];

export function Features() {
  return (
    <section aria-labelledby="features-heading" className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-4 py-16 lg:px-6 lg:py-24">
        <div className="flex max-w-2xl flex-col gap-3">
          <h2 id="features-heading" className="font-display text-3xl leading-tight text-foreground sm:text-5xl">
            The little things that make it stick
          </h2>
          <p className="text-lg text-muted-foreground">
            Everything you need to cook more often and waste less.
          </p>
        </div>
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <li key={feature.title}>
              <Reveal delay={(index % 3) * 80} className="h-full">
                <Card className="h-full transition-transform duration-300 hover:-translate-y-1">
                  <CardContent className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <span className="flex size-11 items-center justify-center rounded-xl bg-primary-surface text-primary">
                        <feature.icon className="size-5" strokeWidth={1.5} aria-hidden />
                      </span>
                      {feature.pro && <Badge variant="outline">Pro</Badge>}
                    </div>
                    <h3 className="text-lg font-semibold text-foreground">{feature.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
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
