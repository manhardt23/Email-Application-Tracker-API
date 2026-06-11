import { MoreHorizontal } from "lucide-react";
import { useState } from "react";

import { ErrorState } from "./ErrorState";
import { Button } from "./ui/Button";
import { Card, CardHeader } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { Skeleton } from "./ui/Skeleton";
import { StatusBadge } from "./ui/StatusBadge";
import { useMarkFollowedUp, useSnoozeFollowUp } from "../hooks/useFollowUps";
import { useToast } from "./ui/Toast";
import { errorMessage } from "../lib/format";
import { statusSwatch } from "../lib/semantic";
import type { FollowUpStalledItem, FollowUpUpcomingItem, FollowUpsResponse } from "../types/api";

type FollowUpsPanelProps = {
  query: {
    data?: FollowUpsResponse;
    isLoading: boolean;
    isError: boolean;
    error: unknown;
    refetch: () => void;
  };
};

function snoozeDefaultDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 10);
}

export function FollowUpsPanel({ query }: FollowUpsPanelProps) {
  const markFollowedUp = useMarkFollowedUp();
  const snooze = useSnoozeFollowUp();
  const toast = useToast();

  const stalled = query.data?.stalled ?? [];
  const upcoming = query.data?.upcoming ?? [];
  const counts = query.data?.counts;
  const empty = !query.isLoading && !query.isError && stalled.length === 0 && upcoming.length === 0;

  return (
    <Card>
      <CardHeader
        title="Follow-ups"
        action={
          counts ? (
            <span className="rounded-full border border-line bg-sunken px-2 py-0.5 font-mono text-[11px] text-text-2">
              {counts.stalled} due · {counts.upcoming} upcoming
            </span>
          ) : null
        }
      />

      {query.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : empty ? (
        <EmptyState
          title="All caught up — no follow-ups due"
          description="Active applications will appear here when they go quiet past the threshold."
        />
      ) : (
        <div className="space-y-5">
          {upcoming.length > 0 ? (
            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3">
                Coming up
              </h3>
              <ul className="space-y-2">
                {upcoming.map((item) => (
                  <UpcomingRow key={item.application_id} item={item} />
                ))}
              </ul>
            </section>
          ) : null}

          {stalled.length > 0 ? (
            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3">
                Needs follow-up
              </h3>
              <ul className="space-y-2">
                {stalled.map((item) => (
                  <StalledRow
                    key={item.application_id}
                    item={item}
                    busy={markFollowedUp.isPending || snooze.isPending}
                    onFollowedUp={() =>
                      markFollowedUp.mutate(
                        { id: item.application_id },
                        {
                          onSuccess: () => toast({ tone: "success", message: "Marked as followed up." }),
                          onError: (e) =>
                            toast({ tone: "error", message: errorMessage(e, "Could not update.") }),
                        },
                      )
                    }
                    onSnooze={() =>
                      snooze.mutate(
                        { id: item.application_id, until: snoozeDefaultDate() },
                        {
                          onSuccess: () => toast({ tone: "success", message: "Snoozed for one week." }),
                          onError: (e) =>
                            toast({ tone: "error", message: errorMessage(e, "Could not snooze.") }),
                        },
                      )
                    }
                  />
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      )}
    </Card>
  );
}

function UpcomingRow({ item }: { item: FollowUpUpcomingItem }) {
  const inLabel = item.in_days === 0 ? "today" : item.in_days === 1 ? "in 1d" : `in ${item.in_days}d`;
  return (
    <li className="flex items-start justify-between gap-3 border-b border-line pb-2 last:border-0 last:pb-0">
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium text-text">
          {item.company} · {item.role}
        </p>
        <p className="mt-0.5 text-[12px] text-text-3">
          {inLabel} · <StatusBadge stage={item.status} />
        </p>
      </div>
    </li>
  );
}

function StalledRow({
  item,
  busy,
  onFollowedUp,
  onSnooze,
}: {
  item: FollowUpStalledItem;
  busy: boolean;
  onFollowedUp: () => void;
  onSnooze: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const actionLabel = item.has_contact && item.contact.name ? `Message ${item.contact.name.split(" ")[0]}` : "Find contact";
  const actionUrl = item.has_contact && item.contact.linkedin_url ? item.contact.linkedin_url : item.linkedin_search_url;

  return (
    <li className="flex items-start gap-2 border-b border-line pb-2 last:border-0 last:pb-0">
      <span
        className={`mt-2 size-2 shrink-0 rounded-full ${item.urgency === "overdue" ? "bg-[#b91c1c]" : "bg-[#b45309]"}`}
        title={item.urgency === "overdue" ? "Overdue" : "Due"}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-text">
          {item.company} · {item.role}
        </p>
        <p className="mt-0.5 text-[12px] text-text-3">
          Quiet {item.days_since_contact}d · {statusSwatch(item.status).label}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="secondary"
          className="whitespace-nowrap"
          onClick={() => window.open(actionUrl, "_blank", "noopener,noreferrer")}
        >
          {actionLabel}
        </Button>
        <div className="relative">
          <Button
            variant="ghost"
            aria-label="Follow-up actions"
            aria-expanded={menuOpen}
            disabled={busy}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <MoreHorizontal className="size-4" />
          </Button>
          {menuOpen ? (
            <>
              <button
                type="button"
                className="fixed inset-0 z-40 cursor-default"
                aria-label="Close menu"
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute right-0 top-full z-50 mt-1 min-w-[10rem] rounded-md border border-line bg-surface py-1 shadow-[0_8px_28px_rgba(0,0,0,0.10)]">
                <button
                  type="button"
                  className="block w-full px-3 py-1.5 text-left text-[13px] text-text-2 hover:bg-sunken"
                  onClick={() => {
                    setMenuOpen(false);
                    onFollowedUp();
                  }}
                >
                  Mark followed up
                </button>
                <button
                  type="button"
                  className="block w-full px-3 py-1.5 text-left text-[13px] text-text-2 hover:bg-sunken"
                  onClick={() => {
                    setMenuOpen(false);
                    onSnooze();
                  }}
                >
                  Snooze 1 week
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </li>
  );
}
