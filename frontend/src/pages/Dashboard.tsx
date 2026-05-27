import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { Card } from "../components/Card";
import { type ApplicationStatusPoint, ApplicationStatusCard } from "../components/cards/ApplicationStatusCard";
import { type ApplicationsOverTimePoint, ApplicationsOverTimeCard } from "../components/cards/ApplicationsOverTimeCard";
import { type RecentApplicationRow, RecentApplicationsCard } from "../components/cards/RecentApplicationsCard";
import { type TopCompany, TopCompaniesCard } from "../components/cards/TopCompaniesCard";
import { api } from "../lib/api";
import { getValidToken } from "../lib/auth";

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

type Kpi = {
  label: string;
  value: string;
  trend: string;
  trendClass: string;
};

type DashboardData = {
  kpis: Kpi[];
  applicationsOverTime: ApplicationsOverTimePoint[];
  recentApplications: RecentApplicationRow[];
  applicationStatus: ApplicationStatusPoint[];
  topCompanies: TopCompany[];
};

const FALLBACK_DASHBOARD_DATA: DashboardData = {
  kpis: [
    { label: "Total Applications", value: "32", trend: "+8 this week", trendClass: "text-emerald-600" },
    { label: "Responses Received", value: "14", trend: "+3 this week", trendClass: "text-emerald-600" },
    { label: "Interviews Scheduled", value: "7", trend: "+1 this week", trendClass: "text-emerald-600" },
    { label: "Response Rate", value: "43%", trend: "-2% from last week", trendClass: "text-rose-600" },
  ],
  applicationsOverTime: [
    { week: "Wk 1", applications: 6 },
    { week: "Wk 2", applications: 8 },
    { week: "Wk 3", applications: 7 },
    { week: "Wk 4", applications: 10 },
    { week: "Wk 5", applications: 9 },
    { week: "Wk 6", applications: 12 },
  ],
  recentApplications: [
    { company: "Stripe", role: "Software Engineer", status: "Interview", dateApplied: "2026-05-20" },
    { company: "Notion", role: "Backend Engineer", status: "Applied", dateApplied: "2026-05-18" },
    { company: "Figma", role: "Platform Engineer", status: "Offer", dateApplied: "2026-05-14" },
    { company: "Datadog", role: "Full Stack Engineer", status: "Rejected", dateApplied: "2026-05-12" },
    { company: "Vercel", role: "Frontend Engineer", status: "Applied", dateApplied: "2026-05-10" },
  ],
  applicationStatus: [
    { name: "Applied", value: 18, color: "#6366f1" },
    { name: "Interview", value: 7, color: "#14b8a6" },
    { name: "Offer", value: 2, color: "#f59e0b" },
    { name: "Rejected", value: 5, color: "#f43f5e" },
  ],
  topCompanies: [
    { company: "Stripe", applications: 4 },
    { company: "Notion", applications: 3 },
    { company: "Figma", applications: 2 },
    { company: "Datadog", applications: 2 },
    { company: "Vercel", applications: 1 },
  ],
};

function normalizeStage(value?: string): "applied" | "interview" | "offer" | "rejected" | "other" {
  const stage = (value ?? "").toLowerCase();
  if (stage === "applied") return "applied";
  if (stage === "interview" || stage === "assessment") return "interview";
  if (stage === "offer") return "offer";
  if (stage === "rejected") return "rejected";
  return "other";
}

function formatDate(value?: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

function startOfWeek(date: Date): Date {
  const local = new Date(date);
  const day = local.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  local.setDate(local.getDate() + diff);
  local.setHours(0, 0, 0, 0);
  return local;
}

function weekLabel(date: Date): string {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function toDashboardData(records: ApplicationRecord[]): DashboardData {
  const total = records.length;
  const statusCounts = records.reduce(
    (acc, item) => {
      const stage = normalizeStage(item.stage);
      acc[stage] += 1;
      return acc;
    },
    { applied: 0, interview: 0, offer: 0, rejected: 0, other: 0 },
  );

  const responses = statusCounts.interview + statusCounts.offer + statusCounts.rejected;
  const responseRate = total > 0 ? Math.round((responses / total) * 100) : 0;

  const kpis: Kpi[] = [
    {
      label: "Total Applications",
      value: String(total),
      trend: `${statusCounts.applied} currently applied`,
      trendClass: "text-emerald-600",
    },
    {
      label: "Responses Received",
      value: String(responses),
      trend: `${statusCounts.rejected} closed outcomes`,
      trendClass: "text-emerald-600",
    },
    {
      label: "Interviews Scheduled",
      value: String(statusCounts.interview),
      trend: `${statusCounts.offer} offers so far`,
      trendClass: "text-emerald-600",
    },
    {
      label: "Response Rate",
      value: `${responseRate}%`,
      trend: "Calculated from live data",
      trendClass: "text-slate-500",
    },
  ];

  const today = new Date();
  const thisWeekStart = startOfWeek(today);
  const weekStarts = Array.from({ length: 6 }, (_, idx) => {
    const date = new Date(thisWeekStart);
    date.setDate(thisWeekStart.getDate() - (5 - idx) * 7);
    return date;
  });
  const weekBins = new Map(weekStarts.map((weekStart) => [weekStart.getTime(), 0]));

  records.forEach((item) => {
    if (!item.last_updated) return;
    const date = new Date(item.last_updated);
    if (Number.isNaN(date.getTime())) return;
    const bucket = startOfWeek(date).getTime();
    if (weekBins.has(bucket)) {
      weekBins.set(bucket, (weekBins.get(bucket) ?? 0) + 1);
    }
  });

  const applicationsOverTime: ApplicationsOverTimePoint[] = weekStarts.map((weekStart) => ({
    week: weekLabel(weekStart),
    applications: weekBins.get(weekStart.getTime()) ?? 0,
  }));

  const recentApplications: RecentApplicationRow[] = [...records]
    .sort((a, b) => {
      const first = new Date(a.last_updated ?? 0).getTime();
      const second = new Date(b.last_updated ?? 0).getTime();
      return second - first;
    })
    .slice(0, 8)
    .map((item) => {
      const stage = normalizeStage(item.stage);
      const status: RecentApplicationRow["status"] =
        stage === "interview" ? "Interview" : stage === "offer" ? "Offer" : stage === "rejected" ? "Rejected" : "Applied";
      return {
        company: item.company?.name ?? (typeof item.company_id === "number" ? `Company #${item.company_id}` : "Unknown"),
        role: item.position ?? "-",
        status,
        dateApplied: formatDate(item.last_updated),
      };
    });

  const topCompaniesMap = records.reduce<Map<string, number>>((acc, item) => {
    const name = item.company?.name ?? (typeof item.company_id === "number" ? `Company #${item.company_id}` : "Unknown");
    acc.set(name, (acc.get(name) ?? 0) + 1);
    return acc;
  }, new Map());

  const topCompanies: TopCompany[] = [...topCompaniesMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([company, applications]) => ({ company, applications }));

  const applicationStatus: ApplicationStatusPoint[] = [
    { name: "Applied", value: statusCounts.applied, color: "#6366f1" },
    { name: "Interview", value: statusCounts.interview, color: "#14b8a6" },
    { name: "Offer", value: statusCounts.offer, color: "#f59e0b" },
    { name: "Rejected", value: statusCounts.rejected, color: "#f43f5e" },
  ];

  return { kpis, applicationsOverTime, recentApplications, applicationStatus, topCompanies };
}

export function Dashboard() {
  const isAuthenticated = Boolean(getValidToken());
  const applicationsQuery = useQuery({
    queryKey: ["dashboard-applications"],
    enabled: isAuthenticated,
    queryFn: async () => {
      const response = await api.get<ApplicationRecord[]>("/applications");
      return response.data;
    },
  });

  const liveData = useMemo(
    () => (applicationsQuery.data ? toDashboardData(applicationsQuery.data) : null),
    [applicationsQuery.data],
  );

  const dashboardData = liveData ?? FALLBACK_DASHBOARD_DATA;
  const isUsingLiveData = Boolean(isAuthenticated && liveData);

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Email Application Tracker</h2>
          <p className="mt-1 text-sm text-slate-600">
            Track applications, monitor responses, and visualize your job search.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              isUsingLiveData ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
            }`}
          >
            {isUsingLiveData ? "Live data" : "Demo data"}
          </span>
          <button
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            Export
          </button>
          <button
            type="button"
            className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-700"
          >
            + Add Application
          </button>
        </div>
      </header>

      {isAuthenticated && applicationsQuery.isLoading ? (
        <Card>
          <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            Loading live dashboard data...
          </p>
        </Card>
      ) : null}

      {isAuthenticated && applicationsQuery.isError ? (
        <Card>
          <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            Live dashboard data is unavailable for this account right now. Showing demo data instead.
          </p>
        </Card>
      ) : null}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {dashboardData.kpis.map((kpi) => (
          <Card key={kpi.label}>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{kpi.label}</p>
            <p className="mt-3 text-3xl font-bold text-slate-900">{kpi.value}</p>
            <p className={`mt-2 text-xs font-medium ${kpi.trendClass}`}>{kpi.trend}</p>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <ApplicationsOverTimeCard data={dashboardData.applicationsOverTime} />
          <RecentApplicationsCard rows={dashboardData.recentApplications} />
        </div>
        <div className="space-y-4">
          <ApplicationStatusCard data={dashboardData.applicationStatus} />
          <TopCompaniesCard companies={dashboardData.topCompanies} />
        </div>
      </section>
    </section>
  );
}
