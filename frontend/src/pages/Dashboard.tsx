import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Card, CardHeader } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPill } from "../components/ui/FilterPill";
import { MetricCard } from "../components/ui/MetricCard";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Table, Td, Th, Tr } from "../components/ui/Table";
import {
  useApplicationsOverTime,
  useDashboardGlance,
  useRecentApplications,
  useRoleBreakdown,
  type TrendGranularity,
} from "../hooks/useDashboard";
import type { DashboardGlance, RoleGroupBreakdown } from "../types/api";

const RANGES = [
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
  { days: 180, label: "180 days" },
  { days: 0, label: "All time" },
] as const;

const FUNNEL_COLORS: Record<string, string> = {
  Applied: "#4f46e5",
  Interview: "#57534e",
  Offer: "#15803d",
  Rejected: "#a8a29e",
};

type TrendRange = (typeof RANGES)[number]["days"];

export function Dashboard() {
  const [range, setRange] = useState<TrendRange>(90);
  const [granularity, setGranularity] = useState<Exclude<TrendGranularity, "day">>("week");
  const [roleId, setRoleId] = useState<string | null>(null);

  const glance = useDashboardGlance();
  const overTime = useApplicationsOverTime(range, granularity);
  const roles = useRoleBreakdown();
  const recent = useRecentApplications(8);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Overview of your job search pipeline" />

      <Glance glance={glance} />

      <Card className="mt-3.5">
        <CardHeader
          className="flex-wrap"
          title="Applications over time"
          action={
            <div className="flex flex-wrap items-center gap-1.5">
              <FilterPill
                active={granularity === "week"}
                onClick={() => setGranularity("week")}
              >
                Week
              </FilterPill>
              <FilterPill
                active={granularity === "month"}
                onClick={() => setGranularity("month")}
              >
                Month
              </FilterPill>
              <span className="mx-1 hidden h-4 w-px bg-line sm:inline-block" aria-hidden />
              {RANGES.map((item) => (
                <FilterPill
                  key={item.label}
                  active={range === item.days}
                  onClick={() => setRange(item.days)}
                >
                  {item.label}
                </FilterPill>
              ))}
            </div>
          }
        />
        {overTime.isLoading ? (
          <Skeleton className="h-[200px] w-full" />
        ) : overTime.isError ? (
          <ErrorState error={overTime.error} onRetry={() => overTime.refetch()} />
        ) : (overTime.data ?? []).length === 0 ? (
          <EmptyState
            title="No applications yet."
            description="Weekly and monthly counts appear once an application has an applied date."
          />
        ) : (
          <div style={{ minHeight: 200 }}>
            <ResponsiveContainer width="100%" height={200}>
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

      <div className="mt-3.5 grid grid-cols-1 gap-3.5 lg:grid-cols-[1fr_1.4fr]">
        <Card>
          <Roles
            loading={roles.isLoading}
            error={roles.error}
            onRetry={() => roles.refetch()}
            isError={roles.isError}
            groups={roles.data?.groups ?? []}
            roleId={roleId}
            onSelect={setRoleId}
          />
        </Card>

        <Card>
          <CardHeader title="Recent applications" />
          {recent.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : recent.isError ? (
            <ErrorState error={recent.error} onRetry={() => recent.refetch()} />
          ) : (recent.data ?? []).length === 0 ? (
            <EmptyState
              title="No applications yet."
              description="Promote an email or trigger a check to populate this list."
            />
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
                {(recent.data ?? []).map((row, i) => (
                  <Tr key={`${row.company}-${row.role}-${i}`}>
                    <Td className="font-medium text-text">{row.company}</Td>
                    <Td>{row.role}</Td>
                    <Td>
                      <StatusBadge stage={row.status} />
                    </Td>
                    <Td className="font-mono text-text-3">{row.date_applied}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}

function Glance({
  glance,
}: {
  glance: ReturnType<typeof useDashboardGlance>;
}) {
  if (glance.isError) {
    return <ErrorState error={glance.error} onRetry={() => glance.refetch()} />;
  }
  if (glance.isLoading || !glance.data) {
    return (
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-[1.3fr_1fr]">
        <Skeleton className="h-[148px] w-full" />
        <div className="grid grid-cols-2 gap-3.5">
          <Skeleton className="h-[88px]" />
          <Skeleton className="h-[88px]" />
          <Skeleton className="h-[88px]" />
          <Skeleton className="h-[88px]" />
        </div>
      </div>
    );
  }
  return <GlanceFigures data={glance.data} />;
}

function GlanceFigures({ data }: { data: DashboardGlance }) {
  const funnelTotal = data.funnel.reduce((sum, slice) => sum + slice.value, 0);
  return (
    <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-[1.3fr_1fr]">
      <Card>
        <CardHeader
          title="Status"
          action={
            <span className="font-mono text-[12px] text-text-3">{data.total_applications} total</span>
          }
        />
        <div className="grid grid-cols-4 gap-2">
          {data.funnel.map((slice) => (
            <div key={slice.name}>
              <div className="text-[22px] font-semibold leading-none tracking-[-0.02em] text-text">
                {slice.value}
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[12px] text-text-3">
                <span
                  className="inline-block size-2 rounded-sm"
                  style={{ backgroundColor: FUNNEL_COLORS[slice.name] ?? "#a8a29e" }}
                  aria-hidden
                />
                {slice.name}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex h-1.5 overflow-hidden rounded-sm bg-fill">
          {funnelTotal > 0
            ? data.funnel.map((slice) => (
                <div
                  key={slice.name}
                  style={{
                    width: `${(slice.value / funnelTotal) * 100}%`,
                    backgroundColor: FUNNEL_COLORS[slice.name] ?? "#a8a29e",
                  }}
                />
              ))
            : null}
        </div>
        {data.other_stages > 0 ? (
          <p className="mt-2 text-[12px] text-text-3">
            {data.other_stages} in another stage
          </p>
        ) : null}
      </Card>

      <div className="grid grid-cols-2 gap-3.5">
        <MetricCard
          label="Response rate"
          value={data.response_rate}
          suffix="%"
          title="Interview, offer, and rejected, divided by all applications"
        />
        <MetricCard
          label="This week"
          value={data.this_week}
          hint={`${data.last_week} last week`}
          title="Applied dates in the current calendar week, compared with the previous week"
        />
        <MetricCard
          label="Since last application"
          value={formatDaysSince(data.days_since_last_application)}
        />
        <MetricCard
          label={`Stale · ${data.stale_days} days`}
          value={data.stale_applications}
          hint="No email or update"
          title="No linked email and no application update within the stated number of days"
        />
      </div>
    </div>
  );
}

function formatDaysSince(days: number | null): string {
  if (days === null) return "—";
  if (days <= 0) return "Today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

function Roles({
  loading,
  isError,
  error,
  onRetry,
  groups,
  roleId,
  onSelect,
}: {
  loading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  groups: RoleGroupBreakdown[];
  roleId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const visible = groups.filter((group) => group.applications > 0);
  const selected = visible.find((group) => group.id === roleId) ?? null;

  return (
    <>
      <CardHeader
        title={selected ? selected.label : "Roles"}
        action={
          selected ? (
            <FilterPill onClick={() => onSelect(null)}>All groups</FilterPill>
          ) : null
        }
      />
      {loading ? (
        <Skeleton className="h-32 w-full" />
      ) : isError ? (
        <ErrorState error={error} onRetry={onRetry} />
      ) : visible.length === 0 ? (
        <EmptyState
          title="No applications yet."
          description="Help desk, IT support, NOC, sysadmin, network, and software are grouped from the stored position. Anything else is other."
        />
      ) : selected ? (
        <>
          <p className="mb-3 text-[12px] text-text-3">Titles in this group, from the stored position.</p>
          <BarList
            rows={selected.titles.map((title) => ({
              key: title.title,
              label: title.title || "—",
              applications: title.applications,
            }))}
          />
        </>
      ) : (
        <>
          <p className="mb-3 text-[12px] text-text-3">
            Matched from the stored position. Select a group to see its titles.
          </p>
          <BarList
            rows={visible.map((group) => ({
              key: group.id,
              id: group.id,
              label: group.label,
              applications: group.applications,
            }))}
            onPick={onSelect}
          />
        </>
      )}
    </>
  );
}

function BarList({
  rows,
  onPick,
}: {
  rows: { key: string; label: string; applications: number; id?: string }[];
  onPick?: (id: string) => void;
}) {
  const max = Math.max(...rows.map((row) => row.applications), 1);
  return (
    <ul className="space-y-2.5">
      {rows.map((row) => {
        const body = (
          <>
            <div className="mb-1 flex items-center justify-between gap-3 text-[13px]">
              <span className="truncate text-text-2" title={row.label}>
                {row.label}
              </span>
              <span className="font-mono text-text-3">{row.applications}</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-sm bg-fill">
              <div
                className="h-full rounded-sm bg-accent"
                style={{ width: `${(row.applications / max) * 100}%` }}
              />
            </div>
          </>
        );
        return (
          <li key={row.key}>
            {onPick && row.id ? (
              <button
                type="button"
                className="w-full rounded-sm text-left hover:bg-sunken"
                onClick={() => onPick(row.id!)}
                aria-label={`Show titles in ${row.label}`}
              >
                {body}
              </button>
            ) : (
              body
            )}
          </li>
        );
      })}
    </ul>
  );
}
