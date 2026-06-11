import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, authApi } from "../lib/api";
import { getValidToken, setToken } from "../lib/auth";
import { queryKeys } from "../lib/query-keys";
import type { AuthMe, LoginResponse } from "../types/api";

export function useMe() {
  return useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: async () => (await api.get<AuthMe>("/auth/me")).data,
    enabled: Boolean(getValidToken()),
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      const body = new URLSearchParams(credentials);
      const res = await authApi.post<LoginResponse>("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return res.data;
    },
    onSuccess: (data) => {
      setToken(data.access_token);
      qc.invalidateQueries({ queryKey: queryKeys.auth.me });
    },
  });
}
