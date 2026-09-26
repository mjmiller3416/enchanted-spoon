"use client";
import type { ElementType } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

export function SectionNav<T extends string>({ sections, active, onChange, label }: {
  sections: { id: T; label: string; description: string; icon: ElementType }[];
  active: T;
  onChange: (id: T) => void;
  label: string;
}) {
  return <>
    <div className="lg:hidden">
      <Select value={active} onValueChange={value => onChange(value as T)}>
        <SelectTrigger className="w-full" aria-label={label}><SelectValue /></SelectTrigger>
        <SelectContent>{sections.map(section => <SelectItem key={section.id} value={section.id}>{section.label}</SelectItem>)}</SelectContent>
      </Select>
    </div>
    <Card className="hidden lg:block">
      <CardContent className="p-2">
        <nav aria-label={label} className="space-y-1">
          {sections.map(({ id, label, description, icon: Icon }) => <Button key={id} variant="ghost" aria-current={active === id ? "page" : undefined} onClick={() => onChange(id)} className={cn("h-auto w-full justify-start gap-3 whitespace-normal px-3 py-3 text-left", active === id ? "bg-primary/10 text-primary hover:bg-primary/15" : "text-muted-foreground")}>
            <Icon className="size-5 shrink-0" strokeWidth={1.5} />
            <span className="min-w-0"><span className="block text-sm font-medium">{label}</span><span className="mt-0.5 block text-xs font-normal text-muted-foreground">{description}</span></span>
          </Button>)}
        </nav>
      </CardContent>
    </Card>
  </>;
}
