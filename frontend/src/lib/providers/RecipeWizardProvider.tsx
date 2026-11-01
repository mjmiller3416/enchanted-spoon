"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { RecipeGenerationResponseDTO } from "@/types/ai";

interface RecipeWizardContextValue {
  /** Whether the wizard dialog is open */
  isOpen: boolean;
  /** Current wizard mode */
  mode: "create" | "edit";
  /** Recipe being edited (null in create mode) */
  editRecipeId: number | null;
  /** Pre-generated recipe to seed a create-mode wizard (null otherwise) */
  generatedSeed: RecipeGenerationResponseDTO | null;
  /** Bumps on each seeded open so the wizard remounts with fresh seed data */
  seedKey: number;
  /** Open the wizard to create a new recipe */
  openWizard: () => void;
  /** Open the wizard to edit an existing recipe */
  openWizardForEdit: (recipeId: number) => void;
  /** Open the wizard in create mode, pre-filled from a generated recipe */
  openWizardWithRecipe: (seed: RecipeGenerationResponseDTO) => void;
  /** Share-sheet URL waiting to be imported. */
  importUrl: string | null;
  /** Open URL import for a link shared into the app. */
  openWizardForImport: (url: string) => void;
  /** Close the wizard dialog */
  closeWizard: () => void;
  /** Toggle open/close */
  setOpen: (open: boolean) => void;
}

const RecipeWizardContext = createContext<RecipeWizardContextValue | null>(null);

export function RecipeWizardProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [editRecipeId, setEditRecipeId] = useState<number | null>(null);
  const [generatedSeed, setGeneratedSeed] = useState<RecipeGenerationResponseDTO | null>(null);
  const [importUrl, setImportUrl] = useState<string | null>(null);
  const [seedKey, setSeedKey] = useState(0);

  const openWizard = useCallback(() => {
    setMode("create");
    setEditRecipeId(null);
    setGeneratedSeed(null);
    setImportUrl(null);
    setIsOpen(true);
  }, []);

  const openWizardForEdit = useCallback((recipeId: number) => {
    setMode("edit");
    setEditRecipeId(recipeId);
    setGeneratedSeed(null);
    setIsOpen(true);
  }, []);

  const openWizardWithRecipe = useCallback((seed: RecipeGenerationResponseDTO) => {
    setMode("create");
    setEditRecipeId(null);
    setGeneratedSeed(seed);
    setImportUrl(null);
    setSeedKey((k) => k + 1);
    setIsOpen(true);
  }, []);

  const openWizardForImport = useCallback((url: string) => {
    setMode("create");
    setEditRecipeId(null);
    setGeneratedSeed(null);
    setImportUrl(url);
    setSeedKey((k) => k + 1);
    setIsOpen(true);
  }, []);

  const closeWizard = useCallback(() => setIsOpen(false), []);

  // Reset to a clean create state on close so reopening (edit or seeded) starts
  // fresh — the wizard view is keyed on mode/id/seed and remounts on change.
  const setOpen = useCallback((open: boolean) => {
    setIsOpen(open);
    if (!open) {
      setMode("create");
      setEditRecipeId(null);
      setGeneratedSeed(null);
    }
  }, []);

  return (
    <RecipeWizardContext.Provider
      value={{
        isOpen,
        mode,
        editRecipeId,
        generatedSeed,
        importUrl,
        seedKey,
        openWizard,
        openWizardForEdit,
        openWizardWithRecipe,
        openWizardForImport,
        closeWizard,
        setOpen,
      }}
    >
      {children}
    </RecipeWizardContext.Provider>
  );
}

export function useRecipeWizardDialog() {
  const context = useContext(RecipeWizardContext);
  if (!context) {
    throw new Error(
      "useRecipeWizardDialog must be used within a RecipeWizardProvider"
    );
  }
  return context;
}
