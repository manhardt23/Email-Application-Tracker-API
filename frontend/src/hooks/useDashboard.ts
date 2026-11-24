import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type {
  ApplicationsOverTimePoint,
  DashboardGlance,
  DashboardMetrics,
  RecentApplication,
  RoleBreakdown,
  StatusBreakdownSlice,
} from "../types/api";

export type TrendGranularity = "day" | "week" | "month";

export function useDashboardMetrics() {
  return useQuery({
    queryKey: queryKeys.dashboard.metrics,
    queryFn: async () => (await api.get<DashboardMetrics>("/dashboard/metrics")).data,
  });
}

export function useDashboardGlance() {
  return useQuery({
    queryKey: queryKeys.dashboard.glance,
    queryFn: async () => (await api.get<DashboardGlance>("/dashboard/glance")).data,
  });
}

export function useApplicationsOverTime(days: number, granularity: TrendGranularity) {
  return useQuery({
    queryKey: queryKeys.dashboard.overTime(days, granularity),
    queryFn: async () =>
      (
        await api.get<ApplicationsOverTimePoint[]>("/dashboard/applications-over-time", {
          params: { days, granularity },
        })
      ).data,
  });
}

export function useStatusBreakdown() {
  return useQuery({
    queryKey: queryKeys.dashboard.statusBreakdown,
    queryFn: async () =>
      (await api.get<StatusBreakdownSlice[]>("/dashboard/status-breakdown")).data,
  });
}

export function useRoleBreakdown() {
  return useQuery({
    queryKey: queryKeys.dashboard.roles,
    queryFn: async () => (await api.get<RoleBreakdown>("/dashboard/role-breakdown")).data,
  });
}

export function useRecentApplications(limit = 8) {
  return useQuery({
    queryKey: queryKeys.dashboard.recent,
    queryFn: async () =>
      (await api.get<RecentApplication[]>("/dashboard/recent-applications", { params: { limit } }))
        .data,
  });
}
