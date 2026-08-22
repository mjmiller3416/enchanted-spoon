import { Avatar, AvatarFallback, AvatarImage } from "enchanted-spoon";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl flex flex-wrap items-center gap-4";

// Inline SVG portrait stand-in — remote avatar URLs are CSP-blocked downstream.
const chefPortrait =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#7c5cbf"/><circle cx="32" cy="24" r="11" fill="#e8e2f5"/><path d="M10 60c2-14 11-20 22-20s20 6 22 20z" fill="#e8e2f5"/></svg>'
  );

export const Sizes = () => (
  <div className={frame}>
    <Avatar size="sm">
      <AvatarFallback size="sm">MJ</AvatarFallback>
    </Avatar>
    <Avatar>
      <AvatarFallback>MJ</AvatarFallback>
    </Avatar>
    <Avatar size="lg">
      <AvatarFallback size="lg">MJ</AvatarFallback>
    </Avatar>
    <Avatar size="xl">
      <AvatarFallback size="xl">MJ</AvatarFallback>
    </Avatar>
  </div>
);

export const WithImage = () => (
  <div className={frame}>
    <Avatar size="lg">
      <AvatarImage src={chefPortrait} alt="Morgan James" />
      <AvatarFallback size="lg">MJ</AvatarFallback>
    </Avatar>
    <Avatar size="lg">
      <AvatarImage src="/broken-avatar.png" alt="Priya Patel" />
      <AvatarFallback size="lg">PP</AvatarFallback>
    </Avatar>
  </div>
);

export const ProfileRow = () => (
  <div className="bg-background text-foreground p-6 rounded-xl">
    <div className="flex flex-row items-center gap-3">
      <Avatar>
        <AvatarFallback>MJ</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <div className="text-sm font-medium">Morgan James</div>
        <div className="text-sm text-muted-foreground">Home cook — 42 recipes saved</div>
      </div>
    </div>
  </div>
);
