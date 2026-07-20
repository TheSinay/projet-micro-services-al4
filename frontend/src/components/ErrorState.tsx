import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

/** Actionable error state: clear French message + retry button. */
export function ErrorState({
  message = "Une erreur est survenue lors du chargement.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-16 text-center"
    >
      <AlertTriangle className="h-10 w-10 text-destructive" aria-hidden="true" />
      <p className="text-lg font-semibold">{message}</p>
      {onRetry ? (
        <Button variant="outline" onClick={onRetry}>
          <RotateCcw aria-hidden="true" />
          Réessayer
        </Button>
      ) : null}
    </div>
  );
}
