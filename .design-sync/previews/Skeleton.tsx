import { Card, CardContent, CardHeader, Skeleton } from "enchanted-spoon";

// Cells render on a white card canvas; wrap in the app's own dark surface.
const frame = "bg-background text-foreground p-6 rounded-xl";

export const RecipeCardLoading = () => (
  <div className={frame}>
    <Card className="max-w-sm">
      <Skeleton size="card" shape="none" className="rounded-none" />
      <CardHeader>
        <Skeleton size="lg" className="w-48" />
        <Skeleton className="w-64" />
      </CardHeader>
      <CardContent>
        <div className="flex flex-row items-center gap-3">
          <Skeleton size="avatar" shape="circle" />
          <div className="flex-1 space-y-2">
            <Skeleton size="sm" className="w-32" />
            <Skeleton size="sm" className="w-24" />
          </div>
          <Skeleton size="button-sm" />
        </div>
      </CardContent>
    </Card>
  </div>
);

export const TextAndShapes = () => (
  <div className={`${frame} max-w-md space-y-4`}>
    <Skeleton size="lg" className="w-56" />
    <Skeleton />
    <Skeleton className="w-64" />
    <Skeleton size="sm" className="w-48" />
    <div className="flex flex-row items-center gap-3">
      <Skeleton size="avatar-sm" shape="circle" />
      <Skeleton size="avatar" shape="circle" />
      <Skeleton size="avatar-lg" shape="circle" />
      <Skeleton size="button" />
      <Skeleton size="button-sm" shape="none" />
    </div>
  </div>
);

export const SavedMealsLoading = () => (
  <div className={`${frame} max-w-md space-y-4`}>
    <div className="flex flex-row items-center gap-3">
      <Skeleton size="avatar" shape="circle" />
      <div className="flex-1 space-y-2">
        <Skeleton className="w-44" />
        <Skeleton size="sm" className="w-28" />
      </div>
    </div>
    <div className="flex flex-row items-center gap-3">
      <Skeleton size="avatar" shape="circle" />
      <div className="flex-1 space-y-2">
        <Skeleton className="w-56" />
        <Skeleton size="sm" className="w-36" />
      </div>
    </div>
    <div className="flex flex-row items-center gap-3">
      <Skeleton size="avatar" shape="circle" />
      <div className="flex-1 space-y-2">
        <Skeleton className="w-48" />
        <Skeleton size="sm" className="w-32" />
      </div>
    </div>
  </div>
);
