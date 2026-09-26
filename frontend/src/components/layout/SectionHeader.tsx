import type React from "react";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  icon: React.ElementType;
  title: string;
  description: string;
  accentColor?: "primary" | "secondary";
}

export function SectionHeader({
  icon: Icon,
  title,
  description,
  accentColor = "primary",
}: SectionHeaderProps) {
  return (
    <div className="flex items-start gap-3 mb-6">
      <div
        className={cn(
          "p-2.5 rounded-xl",
          accentColor === "primary" ? "bg-primary/10" : "bg-secondary/10"
        )}
      >
        <Icon
          className={cn(
            "size-5",
            accentColor === "primary" ? "text-primary" : "text-secondary"
          )}
          strokeWidth={1.5}
        />
      </div>
      <div className="min-w-0 flex-1">
        <h2 className="text-section-header text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
      </div>
    </div>
  );
}
