// components/layout/Logo.tsx
interface LogoProps {
  className?: string;
}

/**
 * Whiskful brand mark — the whisk-and-sparkle icon.
 *
 * Renders the shared `/app-icon.svg` so the in-app logo always tracks the
 * source brand asset (edit the SVG and every placement updates). The mark uses
 * a fixed multi-color brand palette that reads on both light and dark themes,
 * so it intentionally does not tint with the surrounding text color.
 *
 * The artwork is taller than it is wide, so size it by height and let the width
 * follow (e.g. `h-8 w-auto`). Avoid forcing a square box (`w-8 h-8`), which an
 * <img> would stretch.
 */
export function Logo({ className }: LogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- static brand vector from /public; next/image adds no value for an inline SVG mark
    <img
      src="/app-icon.svg"
      alt=""
      aria-hidden="true"
      className={className}
    />
  );
}
