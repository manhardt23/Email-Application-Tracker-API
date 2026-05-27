import { AxiosError } from "axios";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../lib/api";

type ApplicationRecord = {
  id: number;
  company_id?: number;
  position?: string;
  stage?: string;
  last_updated?: string;
  notes?: string | null;
  company?: {
    name?: string;
  } | null;
};

type StageFilter = "all" | "applied" | "rejected" | "interview" | "assessment";

type JobTriggerResponse = {
  job_id: string;
  status: string;
};

const STAGE_OPTIONS: Array<{ value: StageFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "applied", label: "Applied" },
  { value: "rejected", label: "Rejected" },
  { value: "interview", label: "Interview" },
  { value: "assessment", label: "Assessment" },
];

const STAGE_BADGE_CLASS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-700",
  interview: "bg-violet-100 text-violet-700",
  assessment: "bg-amber-100 text-amber-700",
  rejected: "bg-rose-100 text-rose-700",
};

function formatDate(value?: string): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function companyLabel(item: ApplicationRecord): string {
  if (item.company?.name) {
    return item.company.name;
  }
  if (typeof item.company_id === "number") {
    return `Company #${item.company_id}`;
  }
  return "Unknown";
}

export function ApplicationsPage() {
  const [stageFilter, setStageFilter] = useState<StageFilter>("all");

  const query = useQuery({
    queryKey: ["applications", stageFilter],
    queryFn: async () => {
      try {
        const response = await api.get<ApplicationRecord[]>("/applications", {
          params: stageFilter === "all" ? undefined : { stage: stageFilter },
        });
        return response.data;
      } catch (error) {
        if (error instanceof AxiosError && error.response?.status === 404) {
          return [];
        }
        throw error;
      }
    },
  });

  const triggerJobMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post<JobTriggerResponse>("/jobs/email-check");
      return response.data;
    },
  });

  const items = query.data ?? [];
  const stageSummary = items.reduce<Record<string, number>>((acc, item) => {
    const key = (item.stage ?? "other").toLowerCase();
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  function stageBadgeClass(stage?: string): string {
    if (!stage) {
      return "bg-slate-100 text-slate-700";
    }
    return STAGE_BADGE_CLASS[stage.toLowerCase()] ?? "bg-slate-100 text-slate-700";
  }

  return (
    <section className="rounded-xl border border-slate-200/80 bg-white/95 p-5 shadow-sm ring-1 ring-white backdrop-blur-sm">
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-lg bg-indigo-100 p-2 text-indigo-700">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M7 9h10" />
            <path d="M7 13h7" />
          </svg>
        </span>
        <h1 className="text-2xl font-semibold text-slate-900">Applications</h1>
      </div>
      <p className="mt-2 text-sm text-slate-600">
        Track stage progression and trigger manual pipeline checks when needed.
      </p>

      <div className="mt-4 flex flex-col gap-3 rounded-lg border border-indigo-100 bg-indigo-50/40 p-3 md:flex-row md:items-end md:justify-between">
        <label className="flex w-full max-w-xs flex-col gap-1 text-sm text-slate-700">
          Stage
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            value={stageFilter}
            onChange={(event) => setStageFilter(event.target.value as StageFilter)}
          >
            {STAGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md bg-gradient-to-r from-indigo-600 to-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition duration-200 hover:scale-[1.01] hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => triggerJobMutation.mutate()}
          disabled={triggerJobMutation.isPending}
        >
          {triggerJobMutation.isPending ? "Triggering..." : "Trigger Job"}
        </button>
      </div>

      {triggerJobMutation.isSuccess ? (
        <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          Job queued: #{triggerJobMutation.data.job_id} ({triggerJobMutation.data.status})
        </p>
      ) : null}

      {triggerJobMutation.isError ? (
        <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          Could not trigger job. Verify admin access and try again.
        </p>
      ) : null}

      {items.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
            Total: {items.length}
          </span>
          {Object.entries(stageSummary).map(([stage, count]) => (
            <span
              key={stage}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${stageBadgeClass(stage)}`}
            >
              {stage}: {count}
            </span>
          ))}
        </div>
      ) : null}

      {query.isLoading ? (
        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3 text-slate-700">
          Loading applications...
        </div>
      ) : null}

      {query.isError ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-600">
          Could not load applications. Verify your access and try again.
        </div>
      ) : null}

      {query.data && query.data.length === 0 ? (
        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3 text-slate-700">
          No applications found for this stage.
        </div>
      ) : null}

      {query.data && query.data.length > 0 ? (
        <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200/80 shadow-sm">
          <table className="min-w-full border-collapse overflow-hidden rounded-lg">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-sm text-slate-600">
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Position</th>
                <th className="px-3 py-2">Stage</th>
                <th className="px-3 py-2">Last Updated</th>
                <th className="px-3 py-2">Notes</th>
              </tr>
            </thead>
            <tbody>
              {query.data.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-slate-100 text-sm text-slate-800 odd:bg-white even:bg-slate-50/40 transition hover:bg-indigo-50/30"
                >
                  <td className="px-3 py-3 font-medium text-slate-900">{companyLabel(item)}</td>
                  <td className="px-3 py-3">{item.position ?? "-"}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${stageBadgeClass(item.stage)}`}
                    >
                      {item.stage ?? "-"}
                    </span>
                  </td>
                  <td className="px-3 py-2">{formatDate(item.last_updated)}</td>
                  <td className="px-3 py-2">{item.notes || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
