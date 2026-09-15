import { afterEach, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { NumberStepper } from "@/components/ui/numeric-stepper";
afterEach(cleanup);

function Example({ initial = 8 }: { initial?: number }) {
  const [value, setValue] = useState(initial);
  return <NumberStepper label="Servings" value={value} onChange={setValue} min={0} max={10} step={5} />;
}
it("clamps button increments and decrements at the limits", () => {
  render(<Example />);
  fireEvent.click(screen.getByRole("button", { name: "Increase Servings" }));
  expect((screen.getByLabelText("Servings") as HTMLInputElement).value).toBe("10");
  fireEvent.click(screen.getByRole("button", { name: "Decrease Servings" }));
  fireEvent.click(screen.getByRole("button", { name: "Decrease Servings" }));
  expect((screen.getByLabelText("Servings") as HTMLInputElement).value).toBe("0");
});
it("allows clearing and replacing the typed value", () => {
  render(<Example />);
  const input = screen.getByLabelText("Servings") as HTMLInputElement;
  fireEvent.change(input, { target: { value: "" } });
  expect(input.value).toBe("");
  fireEvent.change(input, { target: { value: "3" } });
  fireEvent.blur(input);
  expect(input.value).toBe("3");
});
it("forwards form error descriptions to the actual input", () => {
  render(<><p id="error">Choose a quantity</p><NumberStepper id="quantity" label="Quantity" hasError aria-describedby="error" /></>);
  const input = screen.getByLabelText("Quantity");
  expect(input.getAttribute("aria-invalid")).toBe("true");
  expect(input.getAttribute("aria-describedby")).toBe("error");
});
