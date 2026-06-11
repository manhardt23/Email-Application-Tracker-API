import { AlertTriangle } from "lucide-react";

import { errorMessage } from "../lib/format";
import { Button } from "./ui/Button";

export function ErrorState({
  error,
  onRetry,
  fallback,
}: {
  error?: unknown;
  onRetry?: () => void;
  fallback?: string;
}) {
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-3 rounded-md border px-3.5 py-3 text-[13px]"
      style={{
        color: "var(--color-danger-fg)",
        backgroundColor: "var(--color-danger-bg)",
        borderColor: "var(--color-danger-border)",
      }}
    >
      <span className="flex items-center gap-2">
        <AlertTriangle className="size-4 shrink-0" aria-hidden />
        {errorMessage(error, fallback ?? "Could not load this data.")}
      </span>
      {onRetry ? (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
