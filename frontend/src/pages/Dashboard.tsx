import { Card } from "../components/Card";
import { ApplicationStatusCard } from "../components/cards/ApplicationStatusCard";
import { ApplicationsOverTimeCard } from "../components/cards/ApplicationsOverTimeCard";
import { RecentApplicationsCard } from "../components/cards/RecentApplicationsCard";
import { TopCompaniesCard } from "../components/cards/TopCompaniesCard";

const kpis = [
  { label: "Total Applications", value: "32", trend: "+8 this week", trendClass: "text-emerald-600" },
  { label: "Responses Received", value: "14", trend: "+3 this week", trendClass: "text-emerald-600" },
  { label: "Interviews Scheduled", value: "7", trend: "+1 this week", trendClass: "text-emerald-600" },
  { label: "Response Rate", value: "43%", trend: "-2% from last week", trendClass: "text-rose-600" },
];

export function Dashboard() {
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

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <Card key={kpi.label}>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{kpi.label}</p>
            <p className="mt-3 text-3xl font-bold text-slate-900">{kpi.value}</p>
            <p className={`mt-2 text-xs font-medium ${kpi.trendClass}`}>{kpi.trend}</p>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <ApplicationsOverTimeCard />
          <RecentApplicationsCard />
        </div>
        <div className="space-y-4">
          <ApplicationStatusCard />
          <TopCompaniesCard />
        </div>
      </section>
    </section>
  );
}
