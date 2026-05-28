import { AxiosError } from "axios";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Card } from "../components/Card";
import { ApplicationsSummaryCard } from "../components/cards/ApplicationsSummaryCard";
import { ApplicationsTableCard } from "../components/cards/ApplicationsTableCard";
import { ApplicationsToolbarCard, type StageFilter } from "../components/cards/ApplicationsToolbarCard";
import { api } from "../lib/api";

type ApplicationRecord = {
  id: number;
  company_id?: number;
  position?: string;
  stage?: string;
  last_updated?: string;
  company?: {
    name?: string;
  } | null;
};

type JobTriggerResponse = {
  job_id: string;
  status: string;
};

export function Applications() {
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

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Applications</h2>
          <p className="mt-1 text-sm text-slate-600">Track stage progression and trigger manual pipeline checks.</p>
        </div>
        <button
          type="button"
          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => triggerJobMutation.mutate()}
          disabled={triggerJobMutation.isPending}
        >
          {triggerJobMutation.isPending ? "Triggering..." : "Trigger Job"}
        </button>
      </header>

      {triggerJobMutation.isSuccess ? (
        <Card>
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            Job queued: #{triggerJobMutation.data.job_id} ({triggerJobMutation.data.status})
          </p>
        </Card>
      ) : null}

      {triggerJobMutation.isError ? (
        <Card>
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
            Could not trigger job. Verify admin access and try again.
          </p>
        </Card>
      ) : null}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <ApplicationsToolbarCard stageFilter={stageFilter} onStageChange={setStageFilter} />
          {query.isLoading ? (
            <Card>
              <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                Loading applications...
              </p>
            </Card>
          ) : null}
          {query.isError ? (
            <Card>
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
                Could not load applications. Verify your access and try again.
              </p>
            </Card>
          ) : null}
          {query.data && query.data.length === 0 ? (
            <Card>
              <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                No applications found for this stage.
              </p>
            </Card>
          ) : null}
          {query.data && query.data.length > 0 ? <ApplicationsTableCard items={items} /> : null}
        </div>

        <div className="space-y-4">
          <ApplicationsSummaryCard totalCount={items.length} stageSummary={stageSummary} />
        </div>
      </section>
    </section>
  );
}
