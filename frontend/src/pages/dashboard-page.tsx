import { useQuery } from "@tanstack/react-query";

import { Card } from "../components/ui/card";
import { publicApi } from "../lib/api";

type StatsResponse = {
  total_emails_processed: number;
  job_related_emails: number;
  worker_last_ran_at: string | null;
  worker_run_count_7d: number;
};

function formatRelativeTime(timestamp: string | null): string {
  if (!timestamp) {
    return "No completed runs yet";
  }
  const millis = Date.now() - new Date(timestamp).getTime();
  if (Number.isNaN(millis) || millis < 0) {
    return "Unknown";
  }
  const minutes = Math.floor(millis / 60_000);
  if (minutes < 1) {
    return "Just now";
  }
  if (minutes < 60) {
    return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export function DashboardPage() {
  const stats = useQuery({
    queryKey: ["stats"],
    queryFn: async () => {
      const response = await publicApi.get<StatsResponse>("/stats");
      return response.data;
    },
  });

  return (
    <section className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Email Tracker Dashboard</h1>
        <p className="text-sm text-slate-600">Initial SPA shell powered by FastAPI.</p>
      </header>

      {stats.isLoading ? <p className="text-slate-700">Loading stats...</p> : null}
      {stats.isError ? (
        <p className="text-red-600">Could not load stats. Verify the API is reachable and retry.</p>
      ) : null}

      {stats.data ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <p className="text-sm text-slate-600">Total emails processed</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {stats.data.total_emails_processed}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-slate-600">Job-related emails</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {stats.data.job_related_emails}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-slate-600">Worker last ran</p>
            <p className="mt-2 text-lg font-semibold text-slate-900">
              {formatRelativeTime(stats.data.worker_last_ran_at)}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-slate-600">Completed runs (7d)</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{stats.data.worker_run_count_7d}</p>
          </Card>
        </section>
      ) : null}
    </section>
  );
}
