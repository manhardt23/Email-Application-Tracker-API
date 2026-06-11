import { useMutation, useQuery } from "@tanstack/react-query";

import { api, publicApi } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type {
  JobStatus,
  JobTriggerResponse,
  SystemStats,
  WorkerLimitResponse,
} from "../types/api";

const TERMINAL = new Set(["completed", "failed", "error", "cancelled"]);

export function isTerminalStatus(status: string | undefined): boolean {
  return status ? TERMINAL.has(status.toLowerCase()) : false;
}

export function useTriggerEmailCheck() {
  return useMutation({
    mutationFn: async () => (await api.post<JobTriggerResponse>("/jobs/email-check")).data,
  });
}

export function useTriggerBackfill() {
  return useMutation({
    mutationFn: async (body: { from_date: string; to_date?: string; max_emails?: number }) =>
      (await api.post<JobTriggerResponse>("/jobs/email-backfill", body)).data,
  });
}

export function useSetEmailLimit() {
  return useMutation({
    mutationFn: async (max_emails_per_run: number) =>
      (await api.post<WorkerLimitResponse>("/jobs/email-limit", { max_emails_per_run })).data,
  });
}

/** Polls a single job until it reaches a terminal status. */
export function useJobStatus(jobId: string) {
  return useQuery({
    queryKey: queryKeys.jobs.status(jobId),
    queryFn: async () => (await api.get<JobStatus>(`/jobs/${jobId}`)).data,
    refetchInterval: (query) => (isTerminalStatus(query.state.data?.status) ? false : 2000),
    staleTime: 0,
  });
}

/** GET /stats is served at the site root, not under /api/v1. */
export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: async () => (await publicApi.get<SystemStats>("/stats")).data,
    refetchInterval: 60_000,
  });
}
