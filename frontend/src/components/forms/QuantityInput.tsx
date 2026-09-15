"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { parseQuantity } from "@/lib/quantityUtils";
import { formatQuantity } from "@/lib/utils";

interface QuantityInputProps extends Pick<React.ComponentProps<typeof Input>, "id" | "aria-label" | "aria-labelledby" | "aria-describedby" | "aria-invalid"> {
  value: number | null;
  onChange: (value: number | null) => void;
  placeholder?: string;
  className?: string;
}

/**
 * QuantityInput - A smart input for recipe quantities
 *
 * What it does differently from a standard input:
 * 1. Parses fraction inputs: "1/2" or "1 1/2" → stored as 0.5 or 1.5
 * 2. Formats on blur: displays "½" instead of "0.5"
 * 3. Stores numeric value while displaying formatted text
 */
export function QuantityInput({
  value,
  onChange,
  placeholder = "Qty",
  className,
  ...accessibility
}: QuantityInputProps) {
  const [inputText, setInputText] = React.useState(() => formatQuantity(value));
  const [isFocused, setIsFocused] = React.useState(false);

  // Sync input text when value changes externally
  React.useEffect(() => {
    if (!isFocused) {
      setInputText(formatQuantity(value));
    }
  }, [value, isFocused]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newText = e.target.value;
    setInputText(newText);
    onChange(parseQuantity(newText));
  };

  const handleBlur = () => {
    setIsFocused(false);
    // Format the display on blur if we have a valid value
    if (value !== null) {
      setInputText(formatQuantity(value));
    }
  };

  return (
    <Input
      {...accessibility}
      type="text"
      value={inputText}
      onChange={handleChange}
      onFocus={() => setIsFocused(true)}
      onBlur={handleBlur}
      placeholder={placeholder}
      className={className}
    />
  );
}
