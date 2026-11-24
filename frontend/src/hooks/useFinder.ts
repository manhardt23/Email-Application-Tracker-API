import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type { FindJobsResponse, JobSuggestion } from "../types/api";

/** Highest score first. Unscored rows stay last, in their existing order. */
export function sortJobSuggestions(items: JobSuggestion[]): JobSuggestion[] {
  return [...items].sort((a, b) => {
    const aScore = a.importance_score;
    const bScore = b.importance_score;
    if (aScore == null && bScore == null) return 0;
    if (aScore == null) return 1;
    if (bScore == null) return -1;
    return bScore - aScore;
  });
}

export function useJobSuggestions() {
  return useQuery({
    queryKey: queryKeys.finder.suggestions,
    queryFn: async () =>
      sortJobSuggestions((await api.get<JobSuggestion[]>("/finder/suggestions")).data),
  });
}

export function useFindJobs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { query?: string | null }) =>
      (await api.post<FindJobsResponse>("/finder/search", body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.finder.suggestions });
    },
  });
}

export function useDismissSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<{ id: number; dismissed: boolean }>(`/finder/suggestions/${id}/dismiss`))
        .data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.finder.suggestions });
    },
  });
}

export function useApplySuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (
        await api.post<{
          application_id: number;
          company: string;
          position: string;
          stage: string;
          created: boolean;
        }>(`/finder/suggestions/${id}/apply`)
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.finder.suggestions });
      qc.invalidateQueries({ queryKey: queryKeys.applications.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}
