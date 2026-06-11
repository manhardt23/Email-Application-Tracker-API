import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type {
  ApplicationsOverTimePoint,
  DashboardMetrics,
  RecentApplication,
  StatusBreakdownSlice,
  TopCompany,
} from "../types/api";

export function useDashboardMetrics() {
  return useQuery({
    queryKey: queryKeys.dashboard.metrics,
    queryFn: async () => (await api.get<DashboardMetrics>("/dashboard/metrics")).data,
  });
}

export function useApplicationsOverTime(days = 30) {
  return useQuery({
    queryKey: queryKeys.dashboard.overTime(days),
    queryFn: async () =>
      (
        await api.get<ApplicationsOverTimePoint[]>("/dashboard/applications-over-time", {
          params: { days },
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

export function useRecentApplications(limit = 8) {
  return useQuery({
    queryKey: queryKeys.dashboard.recent,
    queryFn: async () =>
      (await api.get<RecentApplication[]>("/dashboard/recent-applications", { params: { limit } }))
        .data,
  });
}

export function useTopCompanies(limit = 5) {
  return useQuery({
    queryKey: queryKeys.dashboard.topCompanies,
    queryFn: async () =>
      (await api.get<TopCompany[]>("/dashboard/top-companies", { params: { limit } })).data,
  });
}
