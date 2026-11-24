import { Card } from "./Card";
import { Skeleton } from "./Skeleton";

export function MetricCard({
  label,
  value,
  suffix,
  hint,
  title,
  loading = false,
}: {
  label: string;
  value: number | string;
  suffix?: string;
  hint?: string;
  title?: string;
  loading?: boolean;
}) {
  return (
    <Card className="p-4" title={title}>
      {loading ? (
        <Skeleton className="h-[31px] w-20" />
      ) : (
        <div className="text-[26px] font-semibold leading-none tracking-[-0.02em] text-text">
          {value}
          {suffix ? <span className="text-text-3">{suffix}</span> : null}
        </div>
      )}
      <div className="mt-2 text-[12px] text-text-3">{label}</div>
      {hint ? <div className="mt-0.5 text-[11px] text-text-3">{hint}</div> : null}
    </Card>
  );
}
