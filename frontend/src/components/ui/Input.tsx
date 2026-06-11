import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

const base =
  "w-full rounded-md border border-line bg-surface text-[13px] text-text " +
  "placeholder:text-text-3 transition-colors " +
  "focus:border-accent focus:outline-none focus-visible:outline-none " +
  "disabled:opacity-50 disabled:cursor-not-allowed";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cn(base, "h-[34px] px-[11px]", className)} {...rest} />;
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...rest }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn(base, "min-h-16 px-[11px] py-2 leading-relaxed", className)}
        {...rest}
      />
    );
  },
);
