"use client";

import { Globe, ImageIcon, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function socialImportHint(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) return null;
  try {
    const host = new URL(trimmed.includes("://") ? trimmed : `https://${trimmed}`).hostname
      .replace(/^www\./, "")
      .toLowerCase();
    const isTikTok = host === "tiktok.com" || host.endsWith(".tiktok.com");
    const isInstagram = host === "instagram.com" || host.endsWith(".instagram.com");
    if (isTikTok || isInstagram) {
      return "TikTok and Instagram imports use the post caption. Private posts, and videos that only say the recipe out loud, can't be imported.";
    }
  } catch {
    return null;
  }
  return null;
}

// ============================================================================
// Props
// ============================================================================

interface UrlImportStepProps {
  url: string;
  setUrl: (value: string) => void;
  isImporting: boolean;
  error: string | null;
  /** Triggered when the user presses Enter in the URL field. */
  onSubmit: () => void;
}

// ============================================================================
// Component
// ============================================================================

export function UrlImportStep({
  url,
  setUrl,
  isImporting,
  error,
  onSubmit,
}: UrlImportStepProps) {
  const socialHint = socialImportHint(url);

  return (
    <div className="space-y-6">
      {/* Subtitle only — title comes from the wizard header */}
      <p className="text-sm text-muted-foreground">
        Paste a recipe page, or a public TikTok or Instagram post, and we&apos;ll
        recreate it here for you to review and edit.
      </p>

      {/* URL Input */}
      <div className="space-y-2">
        <Label htmlFor="import-url">Recipe URL</Label>
        <Input
          id="import-url"
          type="url"
          inputMode="url"
          placeholder="Recipe page, TikTok, or Instagram link"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && url.trim() && !isImporting) {
              e.preventDefault();
              onSubmit();
            }
          }}
          disabled={isImporting}
          autoFocus
        />
      </div>

      {/* What to expect */}
      <Card>
        <CardContent className="space-y-3 pt-4">
          <div className="flex items-start gap-3">
            <Globe className="size-4 mt-0.5 shrink-0 text-muted-foreground" strokeWidth={1.5} />
            <p className="text-sm text-muted-foreground">
              Works with most recipe websites, plus public TikTok and Instagram
              posts. The original link is saved with your recipe for reference.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <ImageIcon className="size-4 mt-0.5 shrink-0 text-muted-foreground" strokeWidth={1.5} />
            <p className="text-sm text-muted-foreground">
              We&apos;ll grab the recipe photo from the site too — you can keep
              it, replace it, or generate a new one with AI on the next step.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Sparkles className="size-4 mt-0.5 shrink-0 text-muted-foreground" strokeWidth={1.5} />
            <p className="text-sm text-muted-foreground">
              Ingredients and steps are converted into your app&apos;s format —
              review everything before saving.
            </p>
          </div>
        </CardContent>
      </Card>

      {socialHint && (
        <p className="text-sm text-muted-foreground">{socialHint}</p>
      )}

      {/* Error */}
      {error && (
        <div role="alert" aria-live="assertive">
          <Card className="border-destructive">
            <CardContent className="py-3">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
