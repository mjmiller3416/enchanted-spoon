import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import {
  AuthLogo,
  AuthScreen,
  authScreenClassName,
} from "@/components/auth/AuthScreen";
import { SignInForm } from "@/components/auth/SignInForm";
import { SignUpForm } from "@/components/auth/SignUpForm";

vi.mock("@clerk/nextjs", () => ({
  useSignIn: () => ({ isLoaded: true, signIn: {}, setActive: vi.fn() }),
  useSignUp: () => ({ isLoaded: true, signUp: {}, setActive: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: ReactNode;
  }) => <a href={href}>{children}</a>,
}));

afterEach(cleanup);

describe("auth screen on short viewports", () => {
  it("scrolls a dynamic viewport instead of centering in 100vh", () => {
    render(
      <AuthScreen>
        <button type="submit">Continue</button>
      </AuthScreen>,
    );

    const shell = document.querySelector("[data-auth-screen]");
    const submit = screen.getByRole("button", { name: "Continue" });
    expect(shell).not.toBeNull();
    expect(shell?.contains(submit)).toBe(true);
    expect(authScreenClassName).toContain("min-h-[100dvh]");
    expect(authScreenClassName).toContain("min-h-[100svh]");
    expect(authScreenClassName).toContain("overflow-y-auto");
    expect(authScreenClassName).not.toMatch(/(?:^|\s)(?:min-)?h-screen(?:\s|$)/);
    expect(shell?.className).toBe(authScreenClassName);
  });

  it("keeps safe-area insets and tightens vertical padding under 500px", () => {
    expect(authScreenClassName).toContain("env(safe-area-inset-top,0px)");
    expect(authScreenClassName).toContain("env(safe-area-inset-bottom,0px)");
    expect(authScreenClassName).toContain("env(safe-area-inset-left,0px)");
    expect(authScreenClassName).toContain("env(safe-area-inset-right,0px)");
    expect(authScreenClassName).toContain("[@media(max-height:500px)]:pt-[max(0.5rem,env(safe-area-inset-top,0px))]");
    expect(authScreenClassName).toContain("[@media(max-height:500px)]:pb-[max(0.5rem,env(safe-area-inset-bottom,0px))]");
  });

  it("hides the decorative logo at short heights on sign-in and sign-up", () => {
    const { unmount } = render(<AuthLogo />);
    const logo = document.querySelector("[data-auth-logo]");
    expect(logo?.className).toContain("[@media(max-height:500px)]:hidden");
    unmount();

    render(<SignInForm />);
    expect(document.querySelector("[data-auth-logo]")?.className).toContain(
      "[@media(max-height:500px)]:hidden",
    );
    expect(screen.getByRole("button", { name: "Continue", exact: true })).toBeTruthy();
    cleanup();

    render(<SignUpForm />);
    expect(document.querySelector("[data-auth-logo]")?.className).toContain(
      "[@media(max-height:500px)]:hidden",
    );
    expect(screen.getByRole("button", { name: "Create account" })).toBeTruthy();
  });
});
