"use client";

import { useEffect } from "react";
import { useRecipeWizardDialog } from "@/lib/providers/RecipeWizardProvider";
import { extractSharedRecipeUrl } from "@/lib/native/share-link";

/** Opens URL import when a share sheet or deep link delivers a recipe URL. */
export function ShareImportListener() {
  const { openWizardForImport } = useRecipeWizardDialog();

  useEffect(() => {
    const onImport = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      const url = typeof detail === "string" ? extractSharedRecipeUrl(detail) : null;
      if (url) openWizardForImport(url);
    };
    window.addEventListener("enchantedspoon:import", onImport);
    return () => window.removeEventListener("enchantedspoon:import", onImport);
  }, [openWizardForImport]);

  return null;
}
