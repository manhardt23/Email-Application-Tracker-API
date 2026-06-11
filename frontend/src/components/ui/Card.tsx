import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/utils";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("relative rounded-md border border-line bg-surface p-4", className)}
      {...rest}
    />
  );
}

export function CardHeader({
  title,
  action,
  className,
}: {
  title: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-3 flex items-center justify-between gap-3", className)}>
      <h3 className="text-[13px] font-semibold text-text">{title}</h3>
      {action}
    </div>
  );
}
