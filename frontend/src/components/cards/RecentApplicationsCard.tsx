import { Card } from "../Card";

export type ApplicationStatus = "Applied" | "Interview" | "Offer" | "Rejected";

export type RecentApplicationRow = {
  company: string;
  role: string;
  status: ApplicationStatus;
  dateApplied: string;
};

type RecentApplicationsCardProps = {
  rows: RecentApplicationRow[];
};

function statusClassName(status: ApplicationStatus): string {
  if (status === "Interview") return "bg-indigo-100 text-indigo-700";
  if (status === "Offer") return "bg-emerald-100 text-emerald-700";
  if (status === "Rejected") return "bg-rose-100 text-rose-700";
  return "bg-slate-100 text-slate-700";
}

export function RecentApplicationsCard({ rows }: RecentApplicationsCardProps) {
  return (
    <Card
      title="Recent Applications"
      action={
        <a href="/applications" className="text-sm font-medium text-indigo-600 transition hover:text-indigo-700">
          View all
        </a>
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
              <th className="px-0 py-2">Company</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Date Applied</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.company}-${row.role}`} className="border-b border-slate-100 last:border-0">
                <td className="px-0 py-3 text-sm font-medium text-slate-800">{row.company}</td>
                <td className="px-3 py-3 text-sm text-slate-700">{row.role}</td>
                <td className="px-3 py-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClassName(row.status)}`}>
                    {row.status}
                  </span>
                </td>
                <td className="px-3 py-3 text-sm text-slate-600">{row.dateApplied}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
