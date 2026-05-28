import { Card } from "../Card";

type ApplicationRecord = {
  id: number;
  company_id?: number;
  position?: string;
  stage?: string;
  last_updated?: string;
  company?: {
    name?: string;
  } | null;
};

type ApplicationsTableCardProps = {
  items: ApplicationRecord[];
};

const STAGE_BADGE_CLASS: Record<string, string> = {
  applied: "bg-emerald-100 text-emerald-700",
  interview: "bg-indigo-100 text-indigo-700",
  assessment: "bg-teal-100 text-teal-700",
  rejected: "bg-rose-100 text-rose-700",
};

function formatDate(value?: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function companyLabel(item: ApplicationRecord): string {
  if (item.company?.name) return item.company.name;
  if (typeof item.company_id === "number") return `Company #${item.company_id}`;
  return "Unknown";
}

function stageBadgeClass(stage?: string): string {
  if (!stage) return "bg-slate-100 text-slate-700";
  return STAGE_BADGE_CLASS[stage.toLowerCase()] ?? "bg-slate-100 text-slate-700";
}

export function ApplicationsTableCard({ items }: ApplicationsTableCardProps) {
  return (
    <Card title="Applications List">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse overflow-hidden rounded-lg">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-sm text-slate-600">
              <th className="px-3 py-2">Application ID</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Position</th>
              <th className="px-3 py-2">Stage</th>
              <th className="px-3 py-2">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-slate-100 text-sm text-slate-800 odd:bg-white even:bg-slate-50/40 transition hover:bg-emerald-50/30"
              >
                <td className="px-3 py-3 font-mono text-xs text-slate-700">{item.id}</td>
                <td className="px-3 py-3 font-medium text-slate-900">{companyLabel(item)}</td>
                <td className="px-3 py-3">{item.position ?? "-"}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${stageBadgeClass(item.stage)}`}>
                    {item.stage ?? "-"}
                  </span>
                </td>
                <td className="px-3 py-2">{formatDate(item.last_updated)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
