import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function QueryError({ title = "Couldn't load this section", message = "Your data is still saved. Check your connection and try again.", onRetry, retrying = false }: { title?: string; message?: string; onRetry: () => void; retrying?: boolean }) {
  return <Card className="border-destructive/30"><CardContent className="flex flex-wrap items-center gap-4 py-6" role="alert">
    <AlertCircle className="size-6 shrink-0 text-destructive" strokeWidth={1.5} />
    <div className="min-w-0 flex-1"><h2 className="text-card-title">{title}</h2><p className="mt-1 text-sm text-muted-foreground">{message}</p></div>
    <Button variant="outline" disabled={retrying} onClick={onRetry}>{retrying && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}Try again</Button>
  </CardContent></Card>;
}
