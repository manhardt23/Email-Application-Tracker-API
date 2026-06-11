import { useMemo, useState } from "react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { PromoteDrawer } from "../components/PromoteDrawer";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ClassificationTag } from "../components/ui/ClassificationTag";
import { EmptyState } from "../components/ui/EmptyState";
import { Skeleton } from "../components/ui/Skeleton";
import { useEmailsForReview } from "../hooks/useEmails";
import { formatDateTime } from "../lib/format";
import type { EmailRow } from "../types/api";

const CONFIDENCE_FRACTION: Record<string, number> = {
  high: 0.9,
  medium: 0.6,
  low: 0.3,
};

function confidenceFraction(value: string | null): number {
  if (!value) return 0.5;
  return CONFIDENCE_FRACTION[value.toLowerCase()] ?? 0.5;
}

export function ReviewQueue() {
  const query = useEmailsForReview();
  const [promoteEmail, setPromoteEmail] = useState<EmailRow | null>(null);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  const items = useMemo(
    () => (query.data ?? []).filter((e) => !dismissed.has(e.id)),
    [query.data, dismissed],
  );

  return (
    <>
      <PageHeader
        title="Review queue"
        subtitle="Low-confidence classifications needing a human decision"
      />

      {query.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-md" />
          ))}
        </div>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No emails to review."
          description="New low-confidence emails will appear here for a human decision."
        />
      ) : (
        <div className="space-y-3">
          {items.map((email) => {
            const frac = confidenceFraction(email.confidence);
            const low = frac <= 0.3;
            return (
              <Card key={email.id}>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto]">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate text-[14px] font-medium text-text">
                        {email.subject || "(no subject)"}
                      </h3>
                      <ClassificationTag email={email} />
                    </div>
                    <p className="mt-1 font-mono text-[12px] text-text-3">
                      {email.sender} · {formatDateTime(email.received_date)}
                    </p>

                    <div className="mt-3 max-w-xs">
                      <div className="mb-1 flex items-center justify-between text-[11px] text-text-3">
                        <span>Confidence</span>
                        <span className="font-mono">{email.confidence ?? "unknown"}</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-sm bg-fill">
                        <div
                          className="h-full rounded-sm"
                          style={{
                            width: `${frac * 100}%`,
                            backgroundColor: low ? "var(--color-warning-fg)" : "var(--color-line-strong)",
                          }}
                        />
                      </div>
                    </div>

                    {email.detected_company || email.detected_position ? (
                      <p className="mt-2 text-[12px] text-text-3">
                        Detected:{" "}
                        <span className="text-text-2">
                          {email.detected_company ?? "—"} · {email.detected_position ?? "—"}
                        </span>
                      </p>
                    ) : null}
                  </div>

                  <div className="flex flex-row gap-2 sm:flex-col">
                    <Button variant="primary" onClick={() => setPromoteEmail(email)}>
                      Promote to application
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setDismissed((prev) => new Set(prev).add(email.id))}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <PromoteDrawer
        email={promoteEmail}
        open={promoteEmail !== null}
        onClose={() => setPromoteEmail(null)}
      />
    </>
  );
}
