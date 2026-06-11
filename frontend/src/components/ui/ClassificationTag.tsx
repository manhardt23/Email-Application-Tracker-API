import { classifyEmail } from "../../lib/semantic";
import type { EmailRow } from "../../types/api";

/** Inline tag derived from an email's classifier output. */
export function ClassificationTag({ email }: { email: EmailRow }) {
  const c = classifyEmail(email);
  return (
    <span
      className="inline-block rounded-sm px-[7px] py-[2px] text-[11px] font-medium"
      style={{ color: c.fg, backgroundColor: c.bg }}
    >
      {c.label}
    </span>
  );
}
