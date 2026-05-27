import { Card } from "../Card";

export type TopCompany = {
  company: string;
  applications: number;
};

type TopCompaniesCardProps = {
  companies: TopCompany[];
};

export function TopCompaniesCard({ companies }: TopCompaniesCardProps) {
  return (
    <Card title="Top Companies">
      <ul className="divide-y divide-slate-100">
        {companies.map((item) => (
          <li key={item.company} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
            <span className="text-sm text-slate-700">{item.company}</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
              {item.applications}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
