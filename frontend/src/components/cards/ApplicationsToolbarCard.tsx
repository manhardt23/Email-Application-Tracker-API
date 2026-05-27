import { Card } from "../Card";

export type StageFilter = "all" | "applied" | "rejected" | "interview" | "assessment";

type ApplicationsToolbarCardProps = {
  stageFilter: StageFilter;
  onStageChange: (value: StageFilter) => void;
};

const STAGE_OPTIONS: Array<{ value: StageFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "applied", label: "Applied" },
  { value: "rejected", label: "Rejected" },
  { value: "interview", label: "Interview" },
  { value: "assessment", label: "Assessment" },
];

export function ApplicationsToolbarCard({ stageFilter, onStageChange }: ApplicationsToolbarCardProps) {
  return (
    <Card title="Filters">
      <label className="flex w-full max-w-xs flex-col gap-1 text-sm text-slate-700">
        Stage
        <select
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
          value={stageFilter}
          onChange={(event) => onStageChange(event.target.value as StageFilter)}
        >
          {STAGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </Card>
  );
}
