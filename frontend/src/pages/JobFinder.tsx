import { useState } from "react";
import { ExternalLink, Search } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import {
  useApplySuggestion,
  useDismissSuggestion,
  useFindJobs,
  useJobSuggestions,
} from "../hooks/useFinder";
import { errorMessage } from "../lib/format";
import type { JobSuggestion } from "../types/api";

export function JobFinder() {
  const suggestions = useJobSuggestions();
  const find = useFindJobs();
  const dismiss = useDismissSuggestion();
  const apply = useApplySuggestion();
  const toast = useToast();
  const [focus, setFocus] = useState("");

  async function handleFind() {
    const query = focus.trim();
    if (!query) {
      toast({ tone: "info", message: "Enter a search." });
      return;
    }
    try {
      const result = await find.mutateAsync({ query });
      if (result.added.length === 0) {
        toast({
          tone: "info",
          message: result.skipped_existing
            ? "No new roles. Matches already in your applications or this list were left off."
            : "No roles came back. Try a different search.",
        });
      } else {
        const count = result.added.length;
        toast({
          tone: "success",
          message: `Added ${count} job${count === 1 ? "" : "s"}.`,
        });
      }
    } catch (e) {
      toast({ tone: "error", message: errorMessage(e, "Could not search for jobs.") });
    }
  }

  function handleDismiss(job: JobSuggestion) {
    dismiss.mutate(job.id, {
      onSuccess: () => toast({ tone: "success", message: "Suggestion dismissed." }),
      onError: (e) =>
        toast({ tone: "error", message: errorMessage(e, "Could not dismiss suggestion.") }),
    });
  }

  function handleApply(job: JobSuggestion) {
    apply.mutate(job.id, {
      onSuccess: () => toast({ tone: "success", message: "Added to applications." }),
      onError: (e) =>
        toast({ tone: "error", message: errorMessage(e, "Could not add to applications.") }),
    });
  }

  return (
    <>
      <PageHeader
        title="Job finder"
        subtitle="Suggested roles you have not applied to, with pay and the company apply page."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3"
            aria-hidden
          />
          <Input
            className="pl-9"
            placeholder="Role or keywords"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            aria-label="Search focus"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleFind();
              }
            }}
          />
        </div>
        <Button variant="primary" loading={find.isPending} onClick={() => void handleFind()}>
          Find jobs
        </Button>
      </div>

      {suggestions.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-md" />
          ))}
        </div>
      ) : suggestions.isError ? (
        <ErrorState error={suggestions.error} onRetry={() => suggestions.refetch()} />
      ) : (suggestions.data ?? []).length === 0 ? (
        <EmptyState
          title="No suggested jobs."
          description="Search for roles. Jobs you already applied to, and suggestions you dismiss, stay off this list."
        />
      ) : (
        <div className="space-y-3">
          {(suggestions.data ?? []).map((job) => (
            <Card key={job.id}>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto]">
                <div className="min-w-0">
                  <h3 className="truncate text-[14px] font-medium text-text">{job.title}</h3>
                  <p className="mt-1 font-mono text-[12px] text-text-3">{job.company}</p>
                  {job.pay ? (
                    <p className="mt-2 text-[13px] text-text">{job.pay}</p>
                  ) : (
                    <p className="mt-2 text-[12px] text-text-3">No pay listed</p>
                  )}
                  {job.requirements_summary ? (
                    <p className="mt-2 line-clamp-2 text-[12px] text-text-2">
                      {job.requirements_summary}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-row gap-2 sm:flex-col">
                  <a
                    href={job.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Apply to ${job.title} at ${job.company}`}
                    className="inline-flex h-[34px] items-center justify-center gap-1.5 rounded-md border border-inverse bg-inverse px-[13px] text-[13px] font-medium text-on-inverse transition-colors hover:bg-[#2a2522]"
                  >
                    Apply
                    <ExternalLink className="size-3.5" aria-hidden />
                  </a>
                  <Button
                    variant="secondary"
                    loading={apply.isPending && apply.variables === job.id}
                    onClick={() => handleApply(job)}
                    aria-label={`Add ${job.title} at ${job.company} to applications`}
                  >
                    Add to applications
                  </Button>
                  <Button
                    variant="secondary"
                    loading={dismiss.isPending && dismiss.variables === job.id}
                    onClick={() => handleDismiss(job)}
                    aria-label={`Dismiss ${job.title} at ${job.company}`}
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
