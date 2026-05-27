import { useQuery } from "@tanstack/react-query";

import { Card } from "../components/Card";
import { type ApplicationStatusPoint, ApplicationStatusCard } from "../components/cards/ApplicationStatusCard";
import { type ApplicationsOverTimePoint, ApplicationsOverTimeCard } from "../components/cards/ApplicationsOverTimeCard";
import { type RecentApplicationRow, RecentApplicationsCard } from "../components/cards/RecentApplicationsCard";
import { type TopCompany, TopCompaniesCard } from "../components/cards/TopCompaniesCard";
import { api } from "../lib/api";
import { getValidToken } from "../lib/auth";

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

type DashboardMetricsResponse = {
  total_applications: number;
  responses_received: number;
  interviews_scheduled: number;
  response_rate: number;
};

type DashboardTrendResponse = {
  day: string;
  label: string;
  applications: number;
};

type DashboardStatusResponse = {
  name: "Applied" | "Interview" | "Offer" | "Rejected";
  value: number;
};

type DashboardRecentResponse = {
  company: string;
  role: string;
  status: RecentApplicationRow["status"];
  date_applied: string;
};

function toLiveDashboardData(payload: {
  metrics: DashboardMetricsResponse;
  trend: DashboardTrendResponse[];
  status: DashboardStatusResponse[];
  recent: DashboardRecentResponse[];
  topCompanies: TopCompany[];
}): DashboardData {
  const kpis: Kpi[] = [
    {
      label: "Total Applications",
      value: String(payload.metrics.total_applications),
      trend: "Live aggregate",
      trendClass: "text-emerald-600",
    },
    {
      label: "Responses Received",
      value: String(payload.metrics.responses_received),
      trend: "Live aggregate",
      trendClass: "text-emerald-600",
    },
    {
      label: "Interviews Scheduled",
      value: String(payload.metrics.interviews_scheduled),
      trend: "Live aggregate",
      trendClass: "text-emerald-600",
    },
    {
      label: "Response Rate",
      value: `${payload.metrics.response_rate}%`,
      trend: "Calculated from API",
      trendClass: "text-slate-500",
    },
  ];

  const applicationsOverTime: ApplicationsOverTimePoint[] = payload.trend.map((point) => ({
    week: point.label,
    applications: point.applications,
  }));

  const applicationStatus: ApplicationStatusPoint[] = payload.status.map((item) => ({
    ...item,
    color:
      item.name === "Applied"
        ? "#6366f1"
        : item.name === "Interview"
          ? "#14b8a6"
          : item.name === "Offer"
            ? "#f59e0b"
            : "#f43f5e",
  }));

  const recentApplications: RecentApplicationRow[] = payload.recent.map((row) => ({
    company: row.company,
    role: row.role,
    status: row.status,
    dateApplied: row.date_applied,
  }));

  return {
    kpis,
    applicationsOverTime,
    recentApplications,
    applicationStatus,
    topCompanies: payload.topCompanies,
  };
}

export function Dashboard() {
  const isAuthenticated = Boolean(getValidToken());
  const dashboardQuery = useQuery({
    queryKey: ["dashboard-live-data"],
    enabled: isAuthenticated,
    queryFn: async () => {
      const [metricsResponse, trendResponse, statusResponse, recentResponse, topCompaniesResponse] = await Promise.all([
        api.get<DashboardMetricsResponse>("/dashboard/metrics"),
        api.get<DashboardTrendResponse[]>("/dashboard/applications-over-time", { params: { days: 30 } }),
        api.get<DashboardStatusResponse[]>("/dashboard/status-breakdown"),
        api.get<DashboardRecentResponse[]>("/dashboard/recent-applications", { params: { limit: 8 } }),
        api.get<TopCompany[]>("/dashboard/top-companies", { params: { limit: 5 } }),
      ]);
      return toLiveDashboardData({
        metrics: metricsResponse.data,
        trend: trendResponse.data,
        status: statusResponse.data,
        recent: recentResponse.data,
        topCompanies: topCompaniesResponse.data,
      });
    },
  });

  const dashboardData = dashboardQuery.data ?? FALLBACK_DASHBOARD_DATA;
  const isUsingLiveData = Boolean(isAuthenticated && dashboardQuery.data);

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

      {isAuthenticated && dashboardQuery.isLoading ? (
        <Card>
          <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            Loading live dashboard data...
          </p>
        </Card>
      ) : null}

      {isAuthenticated && dashboardQuery.isError ? (
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
