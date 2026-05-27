import type { ReactNode } from "react";

type CardProps = {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Card({ title, action, children, className }: CardProps) {
  const baseClassName = "rounded-xl border border-slate-200 bg-white shadow-sm";
  const classes = className ? `${baseClassName} ${className}` : baseClassName;

  return (
    <section className={classes}>
      {title || action ? (
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {action ? <div>{action}</div> : null}
        </header>
      ) : null}
      <div className="p-5">{children}</div>
    </section>
  );
}
