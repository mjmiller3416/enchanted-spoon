import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const search = new URLSearchParams(
  "response_type=code&client_id=abc&redirect_uri=https%3A%2F%2Fchatgpt.com%2Fcb&code_challenge=" +
    "x".repeat(43) +
    "&code_challenge_method=S256&state=s1&scope=mcp"
);

vi.mock("next/navigation", () => ({ useSearchParams: () => search }));
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "clerk-token" }),
  useUser: () => ({ user: { primaryEmailAddress: { emailAddress: "maryann@example.com" } } }),
}));

const check = vi.fn();
const decide = vi.fn();
vi.mock("@/lib/api", () => ({ oauthApi: { check: (...a: unknown[]) => check(...a), decide: (...a: unknown[]) => decide(...a) } }));

import { ConsentCard } from "@/app/oauth/authorize/_components/ConsentCard";

describe("OAuth consent page", () => {
  beforeEach(() => {
    check.mockReset();
    decide.mockReset();
  });
  afterEach(cleanup);

  it("asks the signed-in person and sends Allow with their token", async () => {
    check.mockResolvedValue({ status: "ok", client_name: "ChatGPT", redirect_to: null, message: null });
    decide.mockResolvedValue({ redirect_to: "https://chatgpt.com/cb?code=c1&state=s1" });
    const navigate = vi.fn();
    render(<ConsentCard navigate={navigate} />);

    expect(await screen.findByText(/ChatGPT wants to use Enchanted Spoon as you/)).toBeTruthy();
    expect(screen.getByText("maryann@example.com")).toBeTruthy();
    expect(check.mock.calls[0][0]).toMatchObject({ client_id: "abc", state: "s1", resource: null });

    fireEvent.click(screen.getByRole("button", { name: "Allow" }));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("https://chatgpt.com/cb?code=c1&state=s1"));
    expect(decide).toHaveBeenCalledWith(expect.objectContaining({ client_id: "abc" }), "allow", "clerk-token");
  });

  it("words Alexa's request as shopping-list only", async () => {
    check.mockResolvedValue({ status: "ok", client_name: "Amazon Alexa", scope: "alexa", redirect_to: null, message: null });
    render(<ConsentCard navigate={vi.fn()} />);
    expect(await screen.findByText(/Amazon Alexa wants to add items to your Enchanted Spoon shopping list/)).toBeTruthy();
    expect(screen.queryByText(/see and change everything you can/)).toBeNull();
  });

  it("sends Cancel as a denial", async () => {
    check.mockResolvedValue({ status: "ok", client_name: "ChatGPT", redirect_to: null, message: null });
    decide.mockResolvedValue({ redirect_to: "https://chatgpt.com/cb?error=access_denied" });
    const navigate = vi.fn();
    render(<ConsentCard navigate={navigate} />);
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("https://chatgpt.com/cb?error=access_denied"));
    expect(decide.mock.calls[0][1]).toBe("deny");
  });

  it("shows an untrusted request's error without redirecting", async () => {
    check.mockResolvedValue({ status: "error", client_name: null, redirect_to: null, message: "This app isn't registered." });
    const navigate = vi.fn();
    render(<ConsentCard navigate={navigate} />);
    expect(await screen.findByText("This app isn't registered.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Allow" })).toBeNull();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("sends a malformed but safe request straight back", async () => {
    check.mockResolvedValue({ status: "redirect", client_name: null, redirect_to: "https://chatgpt.com/cb?error=invalid_request", message: null });
    const navigate = vi.fn();
    render(<ConsentCard navigate={navigate} />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("https://chatgpt.com/cb?error=invalid_request"));
  });
});
