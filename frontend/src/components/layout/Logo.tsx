// components/layout/Logo.tsx
interface LogoProps {
  className?: string;
}

/**
 * Enchanted Spoon brand mark — the spoon-and-sparkle icon.
 *
 * Renders the shared `/logo.svg` so the in-app logo always tracks the
 * source brand asset (edit the SVG and every placement updates). The mark uses
 * a fixed multi-color brand palette that reads on both light and dark themes,
 * so it intentionally does not tint with the surrounding text color.
 *
 * The artwork is taller than it is wide, so size it by height and let the width
 * follow (e.g. `h-8 w-auto`). Avoid forcing a square box (`w-8 h-8`), which an
 * <img> would stretch.
 *
 * TODO(rebrand): the raster brand assets are still the legacy whisk art and
 * need regenerating from this spoon mark — favicon (`src/app/favicon.ico`),
 * PWA/app icons (`src/app/icon.png`, `src/app/apple-icon.png`), and the social
 * preview (`src/app/opengraph-image.png`).
 */
export function Logo({ className }: LogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- static brand vector from /public; next/image adds no value for an inline SVG mark
    <img
      src="/logo.svg"
      alt=""
      aria-hidden="true"
      className={className}
    />
  );
}
