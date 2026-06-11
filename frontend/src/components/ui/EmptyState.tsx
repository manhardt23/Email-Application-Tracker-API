import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border-[1.5px] border-dashed border-line-strong px-8 py-[30px] text-center">
      <p className="text-[13px] font-medium text-text">{title}</p>
      {description ? <p className="max-w-sm text-[12px] text-text-3">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
