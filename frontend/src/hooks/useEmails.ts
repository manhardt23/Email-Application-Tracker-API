import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type { EmailRow, PromoteRequest, PromoteResponse } from "../types/api";

const PAGE_SIZE = 50;

export function useEmails(offset: number) {
  return useQuery({
    queryKey: queryKeys.emails.list(offset),
    queryFn: async () =>
      (await api.get<EmailRow[]>("/emails", { params: { limit: PAGE_SIZE, offset } })).data,
  });
}

export function useEmailsForReview() {
  return useQuery({
    queryKey: queryKeys.emails.review,
    queryFn: async () => (await api.get<EmailRow[]>("/emails/review")).data,
  });
}

/** Promote invalidates emails + review + applications + dashboard (design contract). */
export function usePromoteEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ emailId, body }: { emailId: number; body: PromoteRequest }) =>
      (await api.post<PromoteResponse>(`/emails/${emailId}/promote`, body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.emails.all });
      qc.invalidateQueries({ queryKey: queryKeys.emails.review });
      qc.invalidateQueries({ queryKey: queryKeys.applications.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

export { PAGE_SIZE as EMAILS_PAGE_SIZE };
