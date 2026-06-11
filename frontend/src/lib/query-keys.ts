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
  },
  applications: {
    all: ["applications"] as const,
    list: (stage: string) => ["applications", "list", stage] as const,
    detail: (id: number) => ["applications", "detail", id] as const,
  },
  emails: {
    all: ["emails"] as const,
    list: (offset: number) => ["emails", "list", offset] as const,
    review: ["emails", "review"] as const,
  },
  jobs: {
    status: (id: string) => ["jobs", "status", id] as const,
  },
  stats: ["stats"] as const,
};
