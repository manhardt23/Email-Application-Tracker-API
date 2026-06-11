import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Card, CardHeader } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { MetricCard } from "../components/ui/MetricCard";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Table, Td, Th, Tr } from "../components/ui/Table";
import {
  useApplicationsOverTime,
  useDashboardMetrics,
  useRecentApplications,
  useStatusBreakdown,
  useTopCompanies,
} from "../hooks/useDashboard";

const DONUT_COLORS = ["#4f46e5", "#a8a29e", "#d6d3d1", "#78716c"];

export function Dashboard() {
  const metrics = useDashboardMetrics();
  const overTime = useApplicationsOverTime(30);
  const breakdown = useStatusBreakdown();
  const recent = useRecentApplications(8);
  const topCompanies = useTopCompanies(5);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Overview of your job search pipeline" />

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        {metrics.isError ? (
          <div className="col-span-2 md:col-span-4">
            <ErrorState error={metrics.error} onRetry={() => metrics.refetch()} />
          </div>
        ) : (
          <>
            <MetricCard
              label="Total applications"
              value={metrics.data?.total_applications ?? 0}
              loading={metrics.isLoading}
            />
            <MetricCard
              label="Responses received"
              value={metrics.data?.responses_received ?? 0}
              loading={metrics.isLoading}
            />
            <MetricCard
              label="Interviews scheduled"
              value={metrics.data?.interviews_scheduled ?? 0}
              loading={metrics.isLoading}
            />
            <MetricCard
              label="Response rate"
              value={metrics.data?.response_rate ?? 0}
              suffix="%"
              loading={metrics.isLoading}
            />
          </>
        )}
      </div>

      {/* Chart + donut */}
      <div className="mt-3.5 grid grid-cols-1 gap-3.5 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader title="Applications over time" />
          {overTime.isLoading ? (
            <Skeleton className="h-[180px] w-full" />
          ) : overTime.isError ? (
            <ErrorState error={overTime.error} onRetry={() => overTime.refetch()} />
          ) : (
            <div style={{ minHeight: 180 }}>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={overTime.data ?? []} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="#e7e5e4" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11, fill: "#8a8580" }}
                    interval="preserveStartEnd"
                    minTickGap={28}
                    axisLine={{ stroke: "#d6d3d1" }}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: "#8a8580" }}
                    axisLine={false}
                    tickLine={false}
                    width={36}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 6,
                      border: "1px solid #d6d3d1",
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="applications"
                    stroke="#4f46e5"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Status breakdown" />
          {breakdown.isLoading ? (
            <Skeleton className="h-[180px] w-full" />
          ) : breakdown.isError ? (
            <ErrorState error={breakdown.error} onRetry={() => breakdown.refetch()} />
          ) : (breakdown.data ?? []).every((s) => s.value === 0) ? (
            <EmptyState title="No applications yet." description="Status breakdown appears once you have applications." />
          ) : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={150}>
                <PieChart>
                  <Pie
                    data={breakdown.data ?? []}
                    dataKey="value"
                    nameKey="name"
                    innerRadius="55%"
                    outerRadius="90%"
                    paddingAngle={2}
                    stroke="none"
                  >
                    {(breakdown.data ?? []).map((_, i) => (
                      <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 6, border: "1px solid #d6d3d1", fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="flex-1 space-y-1.5">
                {(breakdown.data ?? []).map((s, i) => (
                  <li key={s.name} className="flex items-center gap-2 text-[13px] text-text-2">
                    <span
                      className="inline-block size-2.5 rounded-sm"
                      style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }}
                      aria-hidden
                    />
                    <span className="flex-1">{s.name}</span>
                    <span className="font-mono text-text">{s.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>

      {/* Recent + top companies */}
      <div className="mt-3.5 grid grid-cols-1 gap-3.5 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader title="Recent applications" />
          {recent.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : recent.isError ? (
            <ErrorState error={recent.error} onRetry={() => recent.refetch()} />
          ) : (recent.data ?? []).length === 0 ? (
            <EmptyState title="No applications yet." description="Promote an email or trigger a check to populate this list." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Company</Th>
                  <Th>Role</Th>
                  <Th>Status</Th>
                  <Th>Applied</Th>
                </tr>
              </thead>
              <tbody>
                {(recent.data ?? []).map((r, i) => (
                  <Tr key={i}>
                    <Td className="font-medium text-text">{r.company}</Td>
                    <Td>{r.role}</Td>
                    <Td>
                      <StatusBadge stage={r.status} />
                    </Td>
                    <Td className="font-mono text-text-3">{r.date_applied}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Top companies" />
          {topCompanies.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : topCompanies.isError ? (
            <ErrorState error={topCompanies.error} onRetry={() => topCompanies.refetch()} />
          ) : (topCompanies.data ?? []).length === 0 ? (
            <EmptyState title="No companies yet." />
          ) : (
            <BarList data={topCompanies.data ?? []} />
          )}
        </Card>
      </div>
    </>
  );
}

function BarList({ data }: { data: { company: string; applications: number }[] }) {
  const max = Math.max(...data.map((d) => d.applications), 1);
  return (
    <ul className="space-y-2.5">
      {data.map((d) => (
        <li key={d.company}>
          <div className="mb-1 flex items-center justify-between text-[13px]">
            <span className="truncate text-text-2">{d.company}</span>
            <span className="ml-2 font-mono text-text-3">{d.applications}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-sm bg-fill">
            <div
              className="h-full rounded-sm bg-accent"
              style={{ width: `${(d.applications / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
