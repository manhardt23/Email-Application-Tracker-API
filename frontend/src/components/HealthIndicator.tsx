import { useHealth } from "../hooks/useHealth";

export function HealthIndicator() {
  const { data, isError, isLoading } = useHealth();
  const ok = !isError && data?.status === "ok";

  if (isLoading) {
    return <span className="text-[12px] text-text-3">Checking…</span>;
  }

  return (
    <span className="inline-flex items-center gap-2 text-[12px] text-text-2">
      <span
        className="inline-block size-2 rounded-full"
        style={{
          backgroundColor: ok ? "var(--color-health)" : "var(--color-danger-fg)",
          boxShadow: ok
            ? "0 0 0 3px var(--color-health-halo)"
            : "0 0 0 3px var(--color-danger-border)",
        }}
        aria-hidden
      />
      {ok ? "API healthy" : "API unreachable"}
    </span>
  );
}
