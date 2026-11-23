/** Centralized React Query keys so mutations can invalidate precisely. */
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  health: ["health"] as const,
  dashboard: {
    all: ["dashboard"] as const,
    metrics: ["dashboard", "metrics"] as const,
    glance: ["dashboard", "glance"] as const,
    overTime: (days: number, granularity: string) =>
      ["dashboard", "applications-over-time", days, granularity] as const,
    statusBreakdown: ["dashboard", "status-breakdown"] as const,
    roles: ["dashboard", "role-breakdown"] as const,
    recent: ["dashboard", "recent-applications"] as const,
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
  finder: {
    suggestions: ["finder", "suggestions"] as const,
  },
  stats: ["stats"] as const,
};
