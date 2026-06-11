/** Centralized React Query keys so mutations can invalidate precisely. */
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  health: ["health"] as const,
  dashboard: {
    all: ["dashboard"] as const,
    metrics: ["dashboard", "metrics"] as const,
    overTime: (days: number) => ["dashboard", "applications-over-time", days] as const,
    statusBreakdown: ["dashboard", "status-breakdown"] as const,
    recent: ["dashboard", "recent-applications"] as const,
    topCompanies: ["dashboard", "top-companies"] as const,
    followUps: (staleAfterDays: number, limit: number) =>
      ["dashboard", "follow-ups", staleAfterDays, limit] as const,
  },
  applications: {
    all: ["applications"] as const,
    list: (stage: string, q: string, offset: number) =>
      ["applications", "list", stage, q, offset] as const,
    detail: (id: number) => ["applications", "detail", id] as const,
    emails: (id: number) => ["applications", "emails", id] as const,
  },
  emails: {
    all: ["emails"] as const,
    list: (offset: number) => ["emails", "list", offset] as const,
    review: ["emails", "review"] as const,
  },
  jobs: {
    all: ["jobs"] as const,
    list: ["jobs", "list"] as const,
    status: (id: string) => ["jobs", "status", id] as const,
  },
  stats: ["stats"] as const,
};
