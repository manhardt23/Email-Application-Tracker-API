import { useState } from "react";
import { ExternalLink, Search } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input, Textarea } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import {
  useFindJobs,
  useJobSuggestions,
  useQualificationProfile,
  useSaveQualificationProfile,
} from "../hooks/useFinder";
import { errorMessage } from "../lib/format";
import type { QualificationFit } from "../types/api";

const FIT: Record<QualificationFit, { label: string; fg: string; bg: string; border: string }> = {
  met: { label: "Met", fg: "#15803d", bg: "#eefcf2", border: "#bbf7d0" },
  partial: { label: "Partial", fg: "#b45309", bg: "#fff7ea", border: "#fde68a" },
  gap: { label: "Gap", fg: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
};

function FitTag({ fit }: { fit: QualificationFit }) {
  const tone = FIT[fit] ?? FIT.gap;
  return (
    <span
      className="inline-block shrink-0 rounded-full border px-[9px] py-[3px] text-[11px] font-medium"
      style={{ color: tone.fg, backgroundColor: tone.bg, borderColor: tone.border }}
    >
      {tone.label}
    </span>
  );
}

export function JobFinder() {
  const profile = useQualificationProfile();
  const suggestions = useJobSuggestions();
  const save = useSaveQualificationProfile();
  const find = useFindJobs();
  const toast = useToast();
  const [titles, setTitles] = useState<string | null>(null);
  const [skills, setSkills] = useState<string | null>(null);
  const [focus, setFocus] = useState("");

  const titlesValue = titles ?? profile.data?.target_titles ?? "";
  const skillsValue = skills ?? profile.data?.skills ?? "";
  const busy = save.isPending || find.isPending;

  function handleSave() {
    save.mutate(
      { target_titles: titlesValue, skills: skillsValue },
      {
        onSuccess: () => toast({ tone: "success", message: "Qualifications saved." }),
        onError: (e) =>
          toast({ tone: "error", message: errorMessage(e, "Could not save qualifications.") }),
      },
    );
  }

  async function handleFind() {
    try {
      await save.mutateAsync({ target_titles: titlesValue, skills: skillsValue });
      const result = await find.mutateAsync({ query: focus.trim() ? focus.trim() : null });
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

  return (
    <>
      <PageHeader
        title="Job finder"
        subtitle="Suggested roles you have not applied to, with pay, qualification fit, and the company apply page."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3"
            aria-hidden
          />
          <Input
            className="pl-9"
            placeholder="Role or keywords (optional)"
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
        <Button variant="primary" loading={busy} onClick={() => void handleFind()}>
          Find jobs
        </Button>
      </div>

      <Card className="mb-5">
        <h2 className="text-[13px] font-semibold text-text">Your qualifications</h2>
        <p className="mt-1 text-[12px] text-text-3">
          Target titles and skills, separated by commas or new lines. Each card is marked met,
          partial, or gap against this list.
        </p>
        {profile.isError ? (
          <div className="mt-3">
            <ErrorState error={profile.error} onRetry={() => profile.refetch()} />
          </div>
        ) : (
          <>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="block text-[12px] text-text-2">
                Target titles
                <Textarea
                  className="mt-1"
                  rows={3}
                  value={titlesValue}
                  onChange={(e) => setTitles(e.target.value)}
                  placeholder="Backend engineer, data analyst"
                  disabled={profile.isLoading}
                />
              </label>
              <label className="block text-[12px] text-text-2">
                Skills
                <Textarea
                  className="mt-1"
                  rows={3}
                  value={skillsValue}
                  onChange={(e) => setSkills(e.target.value)}
                  placeholder="Python, SQL, FastAPI"
                  disabled={profile.isLoading}
                />
              </label>
            </div>
            <div className="mt-3 flex justify-end">
              <Button variant="secondary" loading={save.isPending} onClick={handleSave}>
                Save profile
              </Button>
            </div>
          </>
        )}
      </Card>

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
          description="Save your target titles and skills, then find roles. Jobs you already applied to stay off this list."
        />
      ) : (
        <div className="space-y-3">
          {(suggestions.data ?? []).map((job) => (
            <Card key={job.id}>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto]">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-[14px] font-medium text-text">{job.title}</h3>
                    <FitTag fit={job.qualification_fit} />
                  </div>
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
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
