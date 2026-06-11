import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export interface FilterPillProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

export function FilterPill({ active = false, className, children, ...rest }: FilterPillProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(
        "inline-flex items-center rounded-full border px-[11px] py-1 text-[12px] transition-colors",
        active
          ? "border-inverse bg-inverse text-on-inverse"
          : "border-line bg-surface text-text-2 hover:bg-sunken",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
