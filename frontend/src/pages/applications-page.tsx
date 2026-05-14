import { useQuery } from "@tanstack/react-query";

import { AppNavbar } from "../components/app-navbar";
import { api } from "../lib/api";

type ApplicationRecord = {
  id: number;
  company_id?: number;
  position?: string;
  stage?: string;
  last_updated?: string;
  notes?: string | null;
  company?: {
    name?: string;
  } | null;
};

const ACTIVE_STAGES = new Set(["applied", "interview", "assessment", "offer"]);

function formatDate(value?: string): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function companyLabel(item: ApplicationRecord): string {
  if (item.company?.name) {
    return item.company.name;
  }
  if (typeof item.company_id === "number") {
    return `Company #${item.company_id}`;
  }
  return "Unknown";
}

export function ApplicationsPage() {
  const query = useQuery({
    queryKey: ["applications"],
    queryFn: async () => {
      const response = await api.get<ApplicationRecord[]>("/applications");
      return response.data;
    },
  });

  const activeItems = (query.data ?? []).filter((item) =>
    ACTIVE_STAGES.has((item.stage ?? "").toLowerCase()),
  );

  return (
    <main className="min-h-screen bg-slate-100 p-4 md:p-8">
      <div className="mx-auto max-w-6xl">
        <AppNavbar />

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">Active Applications</h1>
          <p className="mt-1 text-sm text-slate-600">
            Showing stages: applied, interview, assessment, offer.
          </p>

          {query.isLoading ? <p className="mt-6 text-slate-700">Loading applications...</p> : null}

          {query.isError ? (
            <p className="mt-6 text-red-600">
              Could not load applications. Verify your access and try again.
            </p>
          ) : null}

          {query.data && activeItems.length === 0 ? (
            <p className="mt-6 text-slate-700">No active applications found.</p>
          ) : null}

          {activeItems.length > 0 ? (
            <div className="mt-6 overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-sm text-slate-600">
                    <th className="px-3 py-2">Company</th>
                    <th className="px-3 py-2">Position</th>
                    <th className="px-3 py-2">Stage</th>
                    <th className="px-3 py-2">Last Updated</th>
                    <th className="px-3 py-2">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {activeItems.map((item) => (
                    <tr key={item.id} className="border-b border-slate-100 text-sm text-slate-800">
                      <td className="px-3 py-2">{companyLabel(item)}</td>
                      <td className="px-3 py-2">{item.position ?? "-"}</td>
                      <td className="px-3 py-2 capitalize">{item.stage ?? "-"}</td>
                      <td className="px-3 py-2">{formatDate(item.last_updated)}</td>
                      <td className="px-3 py-2">{item.notes || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
