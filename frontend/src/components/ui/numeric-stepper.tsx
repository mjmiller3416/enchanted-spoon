import * as React from "react";
import { Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface NumberStepperProps extends Omit<React.ComponentProps<"input">, "value" | "onChange" | "size" | "type"> {
  value?: number;
  onChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  label?: string;
  hasError?: boolean;
}

export function NumberStepper({ value = 0, onChange, min = 0, max = 999, step = 1, unit, label, hasError, id, className, disabled, readOnly, onBlur, ref, ...props }: NumberStepperProps) {
  const generatedId = React.useId();
  const inputId = id ?? generatedId;
  const [draft, setDraft] = React.useState<string | null>(null);
  const clamp = (number: number) => Math.min(max, Math.max(min, number));
  const adjust = (delta: number) => { setDraft(null); onChange?.(clamp(value + delta)); };
  const invalid = hasError || props["aria-invalid"];
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      {label && <Label htmlFor={inputId}>{label}</Label>}
      <div className={cn("flex items-center overflow-hidden rounded-lg border bg-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background", invalid ? "border-destructive" : "border-input")}>
        <Button type="button" variant="ghost" size="icon" className="shrink-0 rounded-none border-r border-border" disabled={disabled || readOnly || value <= min} aria-label={label ? `Decrease ${label}` : "Decrease value"} onClick={() => adjust(-step)}><Minus className="size-4" strokeWidth={1.5} /></Button>
        <Input {...props} ref={ref} id={inputId} type="number" inputMode="decimal" min={min} max={max} step={step} disabled={disabled} readOnly={readOnly} value={draft ?? value} aria-invalid={invalid} className="min-w-12 rounded-none border-0 bg-transparent px-1 text-center shadow-none focus-visible:ring-0" onChange={event => {
          const text = event.target.value;
          setDraft(text);
          if (text !== "" && Number.isFinite(Number(text))) onChange?.(clamp(Number(text)));
        }} onBlur={event => { setDraft(null); onBlur?.(event); }} />
        {unit && <span className="pr-2 text-xs text-muted-foreground">{unit}</span>}
        <Button type="button" variant="ghost" size="icon" className="shrink-0 rounded-none border-l border-border" disabled={disabled || readOnly || value >= max} aria-label={label ? `Increase ${label}` : "Increase value"} onClick={() => adjust(step)}><Plus className="size-4" strokeWidth={1.5} /></Button>
      </div>
    </div>
  );
}
