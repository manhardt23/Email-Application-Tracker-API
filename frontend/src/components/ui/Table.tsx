import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Table({ className, ...rest }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full border-collapse text-[13px]", className)} {...rest} />
    </div>
  );
}

export function Th({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "border-b border-line px-3 pb-2.5 text-left align-bottom",
        "text-[11px] font-semibold uppercase tracking-[0.04em] text-text-3",
        className,
      )}
      {...rest}
    />
  );
}

export function Td({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("border-b border-line px-3 py-3 text-text-2", className)} {...rest} />
  );
}

export function Tr({
  clickable = false,
  className,
  ...rest
}: HTMLAttributes<HTMLTableRowElement> & { clickable?: boolean }) {
  return (
    <tr
      className={cn(clickable && "cursor-pointer transition-colors hover:bg-sunken", className)}
      {...rest}
    />
  );
}
