"use client";

import { Sun, Moon, Monitor, Palette, Check } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SectionHeader } from "../SectionHeader";
import { appConfig } from "@/lib/config";

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
          description={`Customize how ${appConfig.appName} looks on your device`}
          accentColor="secondary"
        />

        <div className="space-y-6">
          {/* Theme Selection */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <Palette strokeWidth={1.5} className="h-3.5 w-3.5 text-muted-foreground" />
              Theme
            </Label>
            <div className="grid grid-cols-3 gap-3 max-w-lg">
              {themeOptions.map((option) => {
                const Icon = option.icon;
                const isSelected = theme === option.value;

                return (
                  <Button variant="outline"
                    aria-pressed={isSelected}
                    key={option.value}
                    onClick={() => onThemeChange(option.value)}
                    className={cn(
                      "relative h-auto flex flex-col items-center gap-2 p-3 sm:p-4 rounded-xl border-2 transition-all duration-200",
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
                      <Icon strokeWidth={1.5}
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
                        <Check strokeWidth={1.5} className="h-4 w-4 text-secondary" />
                      </div>
                    )}
                  </Button>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Choose your preferred color scheme
            </p>
          </div>

        </div>
      </CardContent>
    </Card>
  );
}
