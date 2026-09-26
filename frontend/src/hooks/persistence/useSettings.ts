"use client";
import { useContext } from "react";
import { SettingsContext } from "@/lib/providers/SettingsProvider";
export * from "@/lib/settings";
export function useSettings() {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useSettings requires SettingsProvider");
  return value;
}
