"use client";

import { useRef } from "react";
import { Sparkles, RotateCcw, AlertTriangle, Smartphone } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { SectionHeader } from "../SectionHeader";
import { DEFAULT_SETTINGS } from "@/hooks/persistence/useSettings";

const PLACEHOLDER_TOKEN = "{recipe_name}";

interface AIFeaturesSectionProps {
  imageGenerationPrompt: string;
  onPromptChange: (value: string) => void;
  onResetPrompt: () => void;
  showAssistantFab: boolean;
  onShowAssistantFabChange: (value: boolean) => void;
}

export function AIFeaturesSection({
  imageGenerationPrompt,
  onPromptChange,
  onResetPrompt,
  showAssistantFab,
  onShowAssistantFabChange,
}: AIFeaturesSectionProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const isDefault =
    imageGenerationPrompt === DEFAULT_SETTINGS.aiFeatures.imageGenerationPrompt;
  const hasPlaceholder = imageGenerationPrompt.includes(PLACEHOLDER_TOKEN);

  // Sync scroll between textarea and backdrop
  const handleScroll = () => {
    if (textareaRef.current && backdropRef.current) {
      backdropRef.current.scrollTop = textareaRef.current.scrollTop;
      backdropRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  // Render text with highlighted placeholders
  const renderHighlightedText = () => {
    if (!imageGenerationPrompt) return null;

    const parts = imageGenerationPrompt.split(PLACEHOLDER_TOKEN);
    return parts.map((part, index) => (
      <span key={index}>
        {part}
        {index < parts.length - 1 && (
          <mark className="bg-primary/20 text-primary rounded px-0.5">
            {PLACEHOLDER_TOKEN}
          </mark>
        )}
      </span>
    ));
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={Sparkles}
          title="AI Features"
          description="Configure AI-powered functionality"
          accentColor="primary"
        />

        <div className="space-y-6">
          {/* Image Generation Prompt */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="image-prompt" className="flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-muted-foreground" />
                Image Generation Prompt
              </Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={onResetPrompt}
                disabled={isDefault}
                className="gap-2 text-muted-foreground hover:text-foreground h-8"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset to Default
              </Button>
            </div>

            {/* Highlighted textarea with overlay technique */}
            <div
              className={cn(
                "relative rounded-md bg-background shadow-sm",
                "border border-border",
                "focus-within:ring-2 focus-within:ring-primary/50 focus-within:border-primary"
              )}
            >
              {/* Backdrop layer - renders highlighted text */}
              <div
                ref={backdropRef}
                aria-hidden="true"
                className={cn(
                  "absolute inset-0 overflow-hidden pointer-events-none",
                  "pl-[13px] pr-3 py-2 text-sm leading-[1.625] whitespace-pre-wrap break-words",
                  "font-sans tracking-normal"
                )}
              >
                {renderHighlightedText()}
              </div>

              {/* Textarea layer - transparent text, handles input */}
              <textarea
                ref={textareaRef}
                id="image-prompt"
                placeholder="Enter your custom image generation prompt..."
                value={imageGenerationPrompt}
                onChange={(e) => onPromptChange(e.target.value)}
                onScroll={handleScroll}
                spellCheck={false}
                className={cn(
                  "relative w-full min-h-[120px]",
                  "px-3 py-2 text-sm leading-[1.625]",
                  "bg-transparent text-transparent caret-foreground",
                  "border-none outline-none",
                  "placeholder:text-muted-foreground-foreground",
                  "font-sans tracking-normal rounded-md"
                )}
              />
            </div>

            {/* Placeholder warning */}
            {!hasPlaceholder && (
              <div className="flex items-start gap-2 p-3 bg-secondary/10 rounded-lg border border-secondary/20">
                <AlertTriangle className="h-4 w-4 text-secondary mt-0.5 flex-shrink-0" />
                <p className="text-xs text-secondary">
                  Your prompt must include{" "}
                  <code className="bg-secondary/20 px-1 py-0.5 rounded">
                    {"{recipe_name}"}
                  </code>{" "}
                  placeholder for the recipe name to be inserted.
                </p>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              Customize the prompt used when generating AI images for recipes.
              Use{" "}
              <code className="bg-elevated px-1 py-0.5 rounded">
                {"{recipe_name}"}
              </code>{" "}
              where you want the recipe name inserted.
            </p>
          </div>

          <Separator />

          {/* Mobile assistant quick access */}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label htmlFor="assistant-fab" className="flex items-center gap-2">
                <Smartphone className="h-3.5 w-3.5 text-muted-foreground" />
                Genie quick button
              </Label>
              <p className="text-xs text-muted-foreground">
                Show a floating &ldquo;Ask the Genie&rdquo; button on the Recipes and
                Planner pages on mobile.
              </p>
            </div>
            <Switch
              id="assistant-fab"
              checked={showAssistantFab}
              onCheckedChange={onShowAssistantFabChange}
            />
          </div>

          <Separator />

          {/* Placeholder for future AI features */}
          <div className="bg-elevated rounded-xl p-6 text-center border border-dashed border-border">
            <p className="text-sm text-muted-foreground">More AI features coming soon</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Recipe suggestions, meal planning AI, and more
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
