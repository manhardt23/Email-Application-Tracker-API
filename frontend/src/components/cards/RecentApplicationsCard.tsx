import { Card } from "../Card";

type ApplicationStatus = "Applied" | "Interview" | "Offer" | "Rejected";

const recentApplications: Array<{
  company: string;
  role: string;
  status: ApplicationStatus;
  dateApplied: string;
}> = [
  { company: "Stripe", role: "Software Engineer", status: "Interview", dateApplied: "2026-05-20" },
  { company: "Notion", role: "Backend Engineer", status: "Applied", dateApplied: "2026-05-18" },
  { company: "Figma", role: "Platform Engineer", status: "Offer", dateApplied: "2026-05-14" },
  { company: "Datadog", role: "Full Stack Engineer", status: "Rejected", dateApplied: "2026-05-12" },
  { company: "Vercel", role: "Frontend Engineer", status: "Applied", dateApplied: "2026-05-10" },
];

function statusClassName(status: ApplicationStatus): string {
  if (status === "Interview") return "bg-indigo-100 text-indigo-700";
  if (status === "Offer") return "bg-emerald-100 text-emerald-700";
  if (status === "Rejected") return "bg-rose-100 text-rose-700";
  return "bg-slate-100 text-slate-700";
}

export function RecentApplicationsCard() {
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
            {recentApplications.map((row) => (
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
