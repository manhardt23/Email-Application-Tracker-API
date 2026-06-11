import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type { FollowUpsResponse } from "../types/api";

export function useFollowUps(staleAfterDays = 14, limit = 8) {
  return useQuery({
    queryKey: queryKeys.dashboard.followUps(staleAfterDays, limit),
    queryFn: async () =>
      (
        await api.get<FollowUpsResponse>("/dashboard/follow-ups", {
          params: { stale_after_days: staleAfterDays, limit },
        })
      ).data,
  });
}

export function useMarkFollowedUp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: { id: number; note?: string }) =>
      (await api.post(`/applications/${id}/followed-up`, note ? { note } : {})).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
      qc.invalidateQueries({ queryKey: queryKeys.applications.all });
    },
  });
}

export function useSnoozeFollowUp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, until }: { id: number; until: string }) =>
      (await api.post(`/applications/${id}/snooze`, { until })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
      qc.invalidateQueries({ queryKey: queryKeys.applications.all });
    },
  });
}
