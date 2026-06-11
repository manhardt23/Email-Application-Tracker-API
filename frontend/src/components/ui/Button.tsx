import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "../../lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-inverse text-on-inverse border-inverse hover:bg-[#2a2522] disabled:hover:bg-inverse",
  secondary:
    "bg-surface text-text border-line-strong hover:bg-sunken",
  ghost: "bg-transparent text-text-2 border-transparent hover:bg-sunken",
  danger: "bg-surface text-[#b91c1c] border-[#fecaca] hover:bg-[#fef2f2]",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 px-2.5 text-[12px]",
  md: "h-[34px] px-[13px] text-[13px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", loading = false, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md border font-medium",
        "transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
});
