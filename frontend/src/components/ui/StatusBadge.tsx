import { statusSwatch } from "../../lib/semantic";

/** Pill keyed by application stage. Text label always present (never color-only). */
export function StatusBadge({ stage }: { stage: string | null | undefined }) {
  const s = statusSwatch(stage);
  return (
    <span
      className="inline-block rounded-full border px-[9px] py-[3px] text-[11px] font-medium"
      style={{ color: s.fg, backgroundColor: s.bg, borderColor: s.border }}
    >
      {s.label}
    </span>
  );
}
