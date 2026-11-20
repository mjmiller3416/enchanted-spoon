import { act, cleanup, render, renderHook, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FeedbackDialog } from "@/components/common/FeedbackDialog";
import {
  FEEDBACK_INTRO,
  FEEDBACK_SUPPORT_EMAIL,
  feedbackFailureMessage,
  useFeedbackForm,
} from "@/hooks/forms/useFeedbackForm";
import { ApiError } from "@/lib/api/base";

const mocks = vi.hoisted(() => ({
  submit: vi.fn(),
  getToken: vi.fn(async () => "session-token" as string | null),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: mocks.getToken }),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/meal-planner",
}));

vi.mock("sonner", () => ({
  toast: { success: mocks.toastSuccess, error: mocks.toastError },
}));

vi.mock("@/lib/api", () => ({
  feedbackApi: { submit: mocks.submit },
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mocks.getToken.mockResolvedValue("session-token");
});

describe("feedback copy and failure toast", () => {
  it("tells people the team receives feedback and does not mention a private tracker", () => {
    expect(FEEDBACK_INTRO).toBe(
      "Your feedback goes straight to our team. Please don't include private or sensitive information.",
    );
    expect(FEEDBACK_INTRO).not.toMatch(/\bAI\b/);
    expect(FEEDBACK_INTRO.toLowerCase()).not.toContain("private delivery");

    render(<FeedbackDialog open onOpenChange={() => undefined} />);
    expect(screen.getByText(new RegExp(FEEDBACK_INTRO))).toBeTruthy();
    expect(screen.queryByText(/private delivery/i)).toBeNull();
  });

  it("shows the backend success message", async () => {
    mocks.submit.mockResolvedValue({
      success: true,
      message: "Thanks! We got your feedback.",
      issue_url: null,
    });
    const { result } = renderHook(() => useFeedbackForm());
    act(() => {
      result.current.setCategory("Bug Report");
      result.current.setMessage("The planner froze on save");
    });
    await act(async () => {
      await result.current.handleSubmit();
    });
    expect(mocks.submit).toHaveBeenCalledWith(
      expect.objectContaining({ category: "Bug Report", message: "The planner froze on save" }),
      "session-token",
    );
    expect(mocks.toastSuccess).toHaveBeenCalledWith("Thanks! We got your feedback.");
    expect(mocks.toastError).not.toHaveBeenCalled();
  });

  it("keeps an error toast only for a real failure and names the support email", async () => {
    mocks.submit.mockRejectedValue(new ApiError("API Error: 500", 500));
    const { result } = renderHook(() => useFeedbackForm());
    act(() => {
      result.current.setCategory("Bug Report");
      result.current.setMessage("The planner froze on save");
    });
    await act(async () => {
      await result.current.handleSubmit();
    });
    expect(mocks.toastError).toHaveBeenCalledWith(
      `API Error: 500 Please email ${FEEDBACK_SUPPORT_EMAIL}.`,
    );
    expect(mocks.toastSuccess).not.toHaveBeenCalled();
    expect(feedbackFailureMessage(new Error("nope"))).toContain(FEEDBACK_SUPPORT_EMAIL);
  });

  it("does not call the API when there is no session token", async () => {
    mocks.getToken.mockResolvedValue(null);
    const { result } = renderHook(() => useFeedbackForm());
    act(() => {
      result.current.setCategory("Bug Report");
      result.current.setMessage("The planner froze on save");
    });
    await act(async () => {
      await result.current.handleSubmit();
    });
    expect(mocks.submit).not.toHaveBeenCalled();
    expect(mocks.toastError.mock.calls[0][0]).toContain(FEEDBACK_SUPPORT_EMAIL);
  });
});
