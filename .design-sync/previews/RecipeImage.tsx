import { RecipeImage } from "enchanted-spoon";

// Inline SVG data-URI stands in for a Cloudinary photo (remote URLs are
// CSP-blocked in the preview sandbox).
const DISH_SVG =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360'>" +
      "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>" +
      "<stop offset='0' stop-color='#3a3128'/><stop offset='1' stop-color='#1d1a16'/>" +
      "</linearGradient></defs>" +
      "<rect width='640' height='360' fill='url(#g)'/>" +
      "<circle cx='320' cy='180' r='120' fill='#e8e2d9'/>" +
      "<circle cx='320' cy='180' r='96' fill='#f4b860'/>" +
      "<circle cx='288' cy='160' r='22' fill='#c1502e'/>" +
      "<circle cx='348' cy='150' r='18' fill='#c1502e'/>" +
      "<circle cx='330' cy='205' r='20' fill='#7a9e4f'/>" +
      "<circle cx='285' cy='210' r='14' fill='#7a9e4f'/>" +
    "</svg>"
  );

// No-src fallback: gradient placeholder with ChefHat icon at each iconSize.
export const PlaceholderSizes = () => (
  <div className="bg-background text-foreground p-6 rounded-xl grid grid-cols-3 gap-4 w-full max-w-2xl">
    <div className="aspect-video rounded-lg overflow-hidden">
      <RecipeImage src={null} alt="No photo yet" iconSize="sm" />
    </div>
    <div className="aspect-video rounded-lg overflow-hidden">
      <RecipeImage src={null} alt="No photo yet" iconSize="md" />
    </div>
    <div className="aspect-video rounded-lg overflow-hidden">
      <RecipeImage src={null} alt="No photo yet" iconSize="lg" />
    </div>
  </div>
);

// Loaded image in fill mode, as SavedMealCard renders planner thumbnails.
export const WithImage = () => (
  <div className="bg-background text-foreground p-6 rounded-xl">
    <div className="relative w-64 aspect-video rounded-lg overflow-hidden">
      <RecipeImage
        src={DISH_SVG}
        alt="Bruschetta Shrimp Pasta"
        fill
        iconSize="md"
        showLoadingState={false}
      />
    </div>
  </div>
);
