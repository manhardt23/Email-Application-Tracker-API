import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type {
  FindJobsResponse,
  JobSuggestion,
  QualificationProfile,
} from "../types/api";

export function useQualificationProfile() {
  return useQuery({
    queryKey: queryKeys.finder.profile,
    queryFn: async () => (await api.get<QualificationProfile>("/finder/profile")).data,
  });
}

export function useSaveQualificationProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: QualificationProfile) =>
      (await api.put<QualificationProfile>("/finder/profile", body)).data,
    onSuccess: (saved) => {
      qc.setQueryData(queryKeys.finder.profile, saved);
      qc.invalidateQueries({ queryKey: queryKeys.finder.suggestions });
    },
  });
}

export function useJobSuggestions() {
  return useQuery({
    queryKey: queryKeys.finder.suggestions,
    queryFn: async () => (await api.get<JobSuggestion[]>("/finder/suggestions")).data,
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
