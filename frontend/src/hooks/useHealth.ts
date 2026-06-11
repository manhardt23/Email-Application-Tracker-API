import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { queryKeys } from "../lib/query-keys";
import type { HealthResponse } from "../types/api";

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: async () => (await api.get<HealthResponse>("/health")).data,
    refetchInterval: 30_000,
    retry: false,
    staleTime: 15_000,
  });
}
