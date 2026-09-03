"use client";

import { useState } from "react";
import { Printer } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

export interface PrintOptions {
  showImage: boolean;
  showNotes: boolean;
  showMeta: boolean;
  showNutrition: boolean;
}

interface PrintPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPrint: (options: PrintOptions) => void;
  hasImage: boolean;
  hasNotes: boolean;
  hasNutrition: boolean;
}

export function PrintPreviewDialog({
  open,
  onOpenChange,
  onPrint,
  hasImage,
  hasNotes,
  hasNutrition,
}: PrintPreviewDialogProps) {
  const [options, setOptions] = useState<PrintOptions>({
    showImage: true,
    showNotes: true,
    showMeta: true,
    showNutrition: true,
  });

  const handlePrint = () => {
    onPrint(options);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Printer className="h-5 w-5 text-secondary" />
            Print Recipe
          </DialogTitle>
        </DialogHeader>

        <div className="py-4">
          <p className="text-sm text-muted-foreground mb-4">
            Choose what to include in your printout:
          </p>

          <div className="space-y-4">
            {hasImage && (
              <div className="flex items-center gap-3">
                <Checkbox
                  id="print-image"
                  checked={options.showImage}
                  onCheckedChange={(checked) =>
                    setOptions((prev) => ({ ...prev, showImage: !!checked }))
                  }
                />
                <Label htmlFor="print-image" className="cursor-pointer">
                  Recipe Image
                </Label>
              </div>
            )}

            {hasNotes && (
              <div className="flex items-center gap-3">
                <Checkbox
                  id="print-notes"
                  checked={options.showNotes}
                  onCheckedChange={(checked) =>
                    setOptions((prev) => ({ ...prev, showNotes: !!checked }))
                  }
                />
                <Label htmlFor="print-notes" className="cursor-pointer">
                  Chef&apos;s Notes
                </Label>
              </div>
            )}

            <div className="flex items-center gap-3">
              <Checkbox
                id="print-meta"
                checked={options.showMeta}
                onCheckedChange={(checked) =>
                  setOptions((prev) => ({ ...prev, showMeta: !!checked }))
                }
              />
              <Label htmlFor="print-meta" className="cursor-pointer">
                Servings & Cook Time
              </Label>
            </div>

            {hasNutrition && (
              <div className="flex items-center gap-3">
                <Checkbox
                  id="print-nutrition"
                  checked={options.showNutrition}
                  onCheckedChange={(checked) =>
                    setOptions((prev) => ({ ...prev, showNutrition: !!checked }))
                  }
                />
                <Label htmlFor="print-nutrition" className="cursor-pointer">
                  Nutrition Facts
                </Label>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handlePrint} className="gap-2">
            <Printer className="h-4 w-4" />
            Print
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
