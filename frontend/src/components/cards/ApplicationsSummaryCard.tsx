import { Card } from "../Card";

type ApplicationsSummaryCardProps = {
  totalCount: number;
  stageSummary: Record<string, number>;
};

const STAGE_BADGE_CLASS: Record<string, string> = {
  applied: "bg-emerald-100 text-emerald-700",
  interview: "bg-indigo-100 text-indigo-700",
  assessment: "bg-teal-100 text-teal-700",
  rejected: "bg-rose-100 text-rose-700",
  other: "bg-slate-100 text-slate-700",
};

export function ApplicationsSummaryCard({ totalCount, stageSummary }: ApplicationsSummaryCardProps) {
  return (
    <Card title="Pipeline Summary">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">Total: {totalCount}</span>
        {Object.entries(stageSummary).map(([stage, count]) => (
          <span
            key={stage}
            className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${STAGE_BADGE_CLASS[stage] ?? STAGE_BADGE_CLASS.other}`}
          >
            {stage}: {count}
          </span>
        ))}
      </div>
    </Card>
  );
}
