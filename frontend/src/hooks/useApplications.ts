import { AxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type { Application, ApplicationUpdate } from "../types/api";

/**
 * GET /applications returns 404 when empty and only supports the `stage`
 * filter (no server search/pagination), so empties are normalized to [].
 */
export function useApplications(stage: string) {
  return useQuery({
    queryKey: queryKeys.applications.list(stage),
    queryFn: async () => {
      try {
        const res = await api.get<Application[]>("/applications", {
          params: stage === "all" ? undefined : { stage },
        });
        return res.data;
      } catch (error) {
        if (error instanceof AxiosError && error.response?.status === 404) {
          return [] as Application[];
        }
        throw error;
      }
    },
  });
}

export function useApplication(id: number) {
  return useQuery({
    queryKey: queryKeys.applications.detail(id),
    queryFn: async () => (await api.get<Application>(`/applications/${id}`)).data,
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useUpdateApplication(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ApplicationUpdate) =>
      (await api.put<Application>(`/applications/${id}`, body)).data,
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.applications.detail(id), data);
      qc.invalidateQueries({ queryKey: queryKeys.applications.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}
