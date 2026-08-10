"use client";

import { Sun, Moon, Monitor, Palette, Check } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { SectionHeader } from "../SectionHeader";

interface AppearanceSectionProps {
  theme: "light" | "dark" | "system";
  onThemeChange: (value: "light" | "dark" | "system") => void;
}

const themeOptions = [
  {
    value: "light",
    label: "Light",
    icon: Sun,
    description: "Light background with dark text",
  },
  {
    value: "dark",
    label: "Dark",
    icon: Moon,
    description: "Dark background with light text",
  },
  {
    value: "system",
    label: "System",
    icon: Monitor,
    description: "Follow system preferences",
  },
] as const;

export function AppearanceSection({
  theme,
  onThemeChange,
}: AppearanceSectionProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={Palette}
          title="Appearance"
          description="Customize how Whiskful looks on your device"
          accentColor="secondary"
        />

        <div className="space-y-6">
          {/* Theme Selection */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <Palette className="h-3.5 w-3.5 text-muted-foreground" />
              Theme
            </Label>
            <div className="grid grid-cols-3 gap-3 max-w-lg">
              {themeOptions.map((option) => {
                const Icon = option.icon;
                const isSelected = theme === option.value;

                return (
                  <button
                    key={option.value}
                    onClick={() => onThemeChange(option.value)}
                    className={cn(
                      "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200",
                      isSelected
                        ? "border-secondary bg-secondary/10 shadow-md"
                        : "border-border hover:border-muted hover:bg-hover"
                    )}
                  >
                    <div
                      className={cn(
                        "p-2.5 rounded-lg",
                        isSelected ? "bg-secondary/20" : "bg-elevated"
                      )}
                    >
                      <Icon
                        className={cn(
                          "h-5 w-5",
                          isSelected ? "text-secondary" : "text-muted-foreground"
                        )}
                      />
                    </div>
                    <span
                      className={cn(
                        "text-sm font-medium",
                        isSelected ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {option.label}
                    </span>
                    {isSelected && (
                      <div className="absolute top-2 right-2">
                        <Check className="h-4 w-4 text-secondary" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Choose your preferred color scheme
            </p>
          </div>

          <Separator />

          {/* Future: Accent Color, Font Size, etc. */}
          <div className="bg-elevated rounded-xl p-6 text-center border border-dashed border-border">
            <p className="text-sm text-muted-foreground">
              More appearance options coming soon
            </p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Accent colors, font sizes, and more
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
