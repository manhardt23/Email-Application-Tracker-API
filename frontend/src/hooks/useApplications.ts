import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type { Application, ApplicationUpdate, EmailRow, Paginated } from "../types/api";

export const APPLICATIONS_PAGE_SIZE = 15;

/**
 * GET /applications returns a {items,total,limit,offset} envelope and supports
 * server-side `stage`, `q` search, and `limit`/`offset` pagination.
 */
export function useApplications(stage: string, q: string, offset: number) {
  return useQuery({
    queryKey: queryKeys.applications.list(stage, q, offset),
    queryFn: async () =>
      (
        await api.get<Paginated<Application>>("/applications", {
          params: {
            ...(stage === "all" ? {} : { stage }),
            ...(q.trim() ? { q: q.trim() } : {}),
            limit: APPLICATIONS_PAGE_SIZE,
            offset,
          },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}

/** Emails linked to an application — powers the detail-page timeline. */
export function useApplicationEmails(id: number) {
  return useQuery({
    queryKey: queryKeys.applications.emails(id),
    queryFn: async () => (await api.get<EmailRow[]>(`/applications/${id}/emails`)).data,
    enabled: Number.isFinite(id) && id > 0,
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
