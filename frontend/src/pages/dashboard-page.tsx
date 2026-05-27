import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { Card } from "../components/ui/card";
import { publicApi } from "../lib/api";

type StatsResponse = {
  total_emails_processed: number;
  job_related_emails: number;
  worker_last_ran_at: string | null;
  worker_run_count_7d: number;
};

type MetricTileProps = {
  label: string;
  value: string | number;
  accent: "indigo" | "teal" | "slate";
  icon: ReactNode;
};

function MetricTile({ label, value, accent, icon }: MetricTileProps) {
  const accentClass =
    accent === "indigo"
      ? "border-indigo-100 bg-indigo-50/40 text-indigo-700"
      : accent === "teal"
        ? "border-teal-100 bg-teal-50/40 text-teal-700"
        : "border-slate-200 bg-slate-50/40 text-slate-700";

  return (
    <Card className="transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-600">{label}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
        </div>
        <div className={`rounded-lg border p-2 ${accentClass}`}>{icon}</div>
      </div>
    </Card>
  );
}

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
    <section>
      <header className="mb-6 rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-600 to-teal-600 p-6 text-white shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-100">
          Job Pipeline Intelligence
        </p>
        <h1 className="mt-2 text-3xl font-semibold">Email Application Tracker</h1>
        <p className="mt-2 max-w-2xl text-sm text-indigo-50">
          A production-ready system that parses inbox updates, classifies job activity, and turns them
          into searchable application records.
        </p>
        <div className="mt-4 inline-flex items-center rounded-full border border-white/30 bg-white/10 px-3 py-1 text-xs font-medium text-indigo-50">
          Portfolio-ready full-stack delivery
        </div>
      </header>

      {stats.isLoading ? (
        <Card className="border-slate-200 bg-slate-50/70">
          <p className="text-slate-700">Loading stats...</p>
        </Card>
      ) : null}
      {stats.isError ? (
        <Card className="border-red-200 bg-red-50/70">
          <p className="text-red-600">Could not load stats. Verify the API is reachable and retry.</p>
        </Card>
      ) : null}

      {stats.data ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricTile
            label="Total emails processed"
            value={stats.data.total_emails_processed}
            accent="indigo"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 7l9 6 9-6" />
                <rect x="3" y="5" width="18" height="14" rx="2" />
              </svg>
            }
          />
          <MetricTile
            label="Job-related emails"
            value={stats.data.job_related_emails}
            accent="teal"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 11h8" />
                <path d="M8 15h5" />
                <rect x="3" y="4" width="18" height="16" rx="2" />
              </svg>
            }
          />
          <MetricTile
            label="Worker last ran"
            value={formatRelativeTime(stats.data.worker_last_ran_at)}
            accent="slate"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 3" />
              </svg>
            }
          />
          <MetricTile
            label="Completed runs (7d)"
            value={stats.data.worker_run_count_7d}
            accent="slate"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 19h16" />
                <path d="M7 16l3-4 3 2 4-6" />
              </svg>
            }
          />
        </section>
      ) : null}

      <section className="mt-6 grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card className="transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-indigo-100 p-1 text-indigo-700">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 19h18" />
                  <path d="M7 15l3-3 3 2 4-6" />
                </svg>
              </span>
              <h2 className="text-lg font-semibold text-slate-900">Pipeline Activity (visual preview)</h2>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">Last 7 days</span>
          </div>
          <div className="space-y-3">
            {[78, 62, 89, 71, 56, 84, 68].map((value, idx) => (
              <div key={idx}>
                <div className="mb-1 flex justify-between text-xs text-slate-500">
                  <span>Day {idx + 1}</span>
                  <span>{value}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-teal-500 transition-all"
                    style={{ width: `${value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-teal-100 p-1 text-teal-700">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14" />
                <path d="M12 5v14" />
              </svg>
            </span>
            <h2 className="text-lg font-semibold text-slate-900">Highlights</h2>
          </div>
          <div className="mt-4 space-y-3">
            {[
              "Stage filtering now runs directly from backend endpoint.",
              "Manual job trigger enabled for admin users.",
              "RBAC keeps sensitive pipeline insight private.",
            ].map((item) => (
              <div key={item} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-2">
        <Card className="transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-indigo-100 p-1 text-indigo-700">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 7h16" />
                <path d="M7 12h10" />
                <path d="M9 17h6" />
              </svg>
            </span>
            <h2 className="text-lg font-semibold text-slate-900">What this app does</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            This app ingests email updates, extracts application signals, and keeps stage transitions visible
            so job-search activity stays measurable and actionable.
          </p>
        </Card>
        <Card className="border-amber-200 bg-amber-50/60 transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-amber-100 p-1 text-amber-700">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="4" y="10" width="16" height="10" rx="2" />
                <path d="M8 10V7a4 4 0 118 0v3" />
              </svg>
            </span>
            <h2 className="text-lg font-semibold text-slate-900">Why user insight is limited</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Access is intentionally restricted to protect personal job-search and email metadata. Public/demo
            users get scoped visibility while sensitive records remain private.
          </p>
        </Card>
      </section>

      <section className="mt-6">
        <Card className="transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Recent application preview</h2>
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700">Mock layout</span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse overflow-hidden rounded-lg">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Company</th>
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Momentum</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Stripe", "Software Engineer", "Interview", 82],
                  ["Notion", "Backend Engineer", "Applied", 55],
                  ["Figma", "Platform Engineer", "Assessment", 68],
                ].map(([company, role, status, momentum]) => (
                  <tr
                    key={`${company}-${role}`}
                    className="border-b border-slate-100 text-sm text-slate-700 odd:bg-white even:bg-slate-50/40"
                  >
                    <td className="px-3 py-3 font-medium text-slate-900">{company}</td>
                    <td className="px-3 py-3">{role}</td>
                    <td className="px-3 py-3">
                      <span className="rounded-full bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700">
                        {status}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <div className="h-2 rounded-full bg-slate-100">
                        <div
                          className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-teal-500"
                          style={{ width: `${momentum}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </section>
    </section>
  );
}
