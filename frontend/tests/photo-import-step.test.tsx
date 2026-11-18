import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PhotoImportStep } from "@/app/(app)/recipes/_components/wizard/steps/PhotoImportStep";
import { MethodSelectionStep } from "@/app/(app)/recipes/_components/wizard/steps/MethodSelectionStep";

const BANNED = /\b(ai|gpt|gemini|artificial intelligence)\b/i;

afterEach(() => cleanup());

const photo = {
  id: "1",
  name: "card.jpg",
  previewUrl: "blob:card",
};

describe("photo import step", () => {
  it("shows progress and cancel without dropping the chosen photo", () => {
    const onCancel = vi.fn();
    render(
      <PhotoImportStep
        photos={[photo]}
        maxPhotos={4}
        isPreparing={false}
        isImporting
        error={null}
        canRetry={false}
        onAddFiles={vi.fn()}
        onRemove={vi.fn()}
        onRetry={vi.fn()}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByRole("status").textContent).toContain("Reading the recipe");
    expect(screen.getByRole("progressbar", { name: "Import progress" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
    expect(screen.getByRole("img", { name: /card\.jpg/ }).getAttribute("src")).toBe("blob:card");
    expect(screen.getByRole("status").textContent).not.toMatch(BANNED);
  });

  it("retries without clearing the photo", () => {
    const onRetry = vi.fn();
    render(
      <PhotoImportStep
        photos={[photo]}
        maxPhotos={4}
        isPreparing={false}
        isImporting={false}
        error="We couldn't reach the server. Check your connection and try again."
        canRetry
        onAddFiles={vi.fn()}
        onRemove={vi.fn()}
        onRetry={onRetry}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getAllByAltText(/card\.jpg/)).toHaveLength(1);
    expect(screen.getByRole("alert").textContent).not.toMatch(BANNED);
  });

  it("disables another submit while a read is in flight", () => {
    render(
      <PhotoImportStep
        photos={[photo]}
        maxPhotos={4}
        isPreparing={false}
        isImporting
        error={null}
        canRetry={false}
        onAddFiles={vi.fn()}
        onRemove={vi.fn()}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect((screen.getByRole("button", { name: "Snap a recipe" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Choose photos" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Remove card.jpg" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("method selection", () => {
  it("hides photo import unless the flag is on, and the option does not say AI", () => {
    const hidden = render(<MethodSelectionStep selectedMethod={null} onSelect={vi.fn()} />);
    expect(hidden.queryByRole("button", { name: /Import from photo/ })).toBeNull();
    hidden.unmount();

    render(<MethodSelectionStep selectedMethod={null} onSelect={vi.fn()} photoImportEnabled />);
    const option = screen.getByRole("button", { name: /Import from photo/ });
    expect(option.textContent).toContain("Snap a recipe card");
    expect(option.textContent).not.toMatch(BANNED);
  });
});
