import { forwardRef, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "../../lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...rest }, ref) {
    return (
      <div className="relative inline-flex w-full min-w-[150px]">
        <select
          ref={ref}
          className={cn(
            "h-[34px] w-full appearance-none rounded-md border border-line-strong bg-surface",
            "pl-[11px] pr-8 text-[13px] text-text transition-colors",
            "focus:border-accent focus:outline-none focus-visible:outline-none",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            className,
          )}
          {...rest}
        >
          {children}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-text-3"
          aria-hidden
        />
      </div>
    );
  },
);
