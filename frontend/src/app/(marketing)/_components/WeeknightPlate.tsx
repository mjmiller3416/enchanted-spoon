import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { AVOCADO_CORN_SALAD, RIBEYE_STEAK, SHRIMP_PASTA } from "./examples";

/**
 * A static, labeled example of one dinner on the weekly menu.
 * Not a screenshot of a customer account.
 */
export function WeeknightPlate() {
  return (
    <figure className="mx-auto flex w-full max-w-lg flex-col gap-4" aria-label="Example Tuesday dinner on a weekly menu">
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-floating">
        <div className="relative aspect-[4/3] bg-elevated">
          <Image
            src={SHRIMP_PASTA.image}
            alt=""
            fill
            priority
            sizes="(max-width: 1024px) 100vw, 512px"
            className="object-cover"
          />
        </div>
        <figcaption className="flex flex-col gap-3 p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-transparent bg-primary-surface text-primary-on-surface">
              Tuesday
            </Badge>
            <Badge variant="outline">Example</Badge>
          </div>
          <p className="font-display text-2xl leading-tight text-foreground sm:text-3xl">
            {SHRIMP_PASTA.name}
          </p>
          <p className="text-sm text-muted-foreground">
            {SHRIMP_PASTA.mealType} · {SHRIMP_PASTA.time} · {SHRIMP_PASTA.servings} servings
          </p>
        </figcaption>
      </div>

      <Card className="gap-3 p-3 shadow-raised">
        <p className="px-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Also on this example menu
        </p>
        <MenuLine day="Tue" name={AVOCADO_CORN_SALAD.name} detail={`${AVOCADO_CORN_SALAD.mealType} · ${AVOCADO_CORN_SALAD.time}`} image={AVOCADO_CORN_SALAD.image} highlighted />
        <MenuLine day="Mon" name={RIBEYE_STEAK.name} detail={`${RIBEYE_STEAK.time} · ${RIBEYE_STEAK.servings} servings`} image={RIBEYE_STEAK.image} />
      </Card>
    </figure>
  );
}

function MenuLine({
  day,
  name,
  detail,
  image,
  highlighted = false,
}: {
  day: string;
  name: string;
  detail: string;
  image: string;
  highlighted?: boolean;
}) {
  return (
    <div
      className={
        highlighted
          ? "flex items-center gap-3 rounded-lg border border-primary bg-primary-surface p-2"
          : "flex items-center gap-3 rounded-lg border border-border bg-background p-2"
      }
    >
      <span className="w-8 shrink-0 text-xs font-medium text-muted-foreground">{day}</span>
      <span className="relative size-10 shrink-0 overflow-hidden rounded-md bg-elevated">
        <Image src={image} alt="" fill sizes="40px" className="object-cover" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">{name}</span>
        <span className="block truncate text-xs text-muted-foreground">{detail}</span>
      </span>
    </div>
  );
}
