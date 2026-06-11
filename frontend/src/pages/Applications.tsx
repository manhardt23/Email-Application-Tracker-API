import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPill } from "../components/ui/FilterPill";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Table, Td, Th, Tr } from "../components/ui/Table";
import { useApplications } from "../hooks/useApplications";
import { formatDate } from "../lib/format";
import { STAGE_OPTIONS, statusSwatch } from "../lib/semantic";

const PAGE_SIZE = 15;
const FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  ...STAGE_OPTIONS.map((s) => ({ value: s, label: statusSwatch(s).label })),
];

export function Applications() {
  const navigate = useNavigate();
  const [stage, setStage] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const query = useApplications(stage);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    const rows = query.data ?? [];
    if (!term) return rows;
    return rows.filter(
      (a) =>
        (a.company?.name ?? "").toLowerCase().includes(term) ||
        a.position.toLowerCase().includes(term),
    );
  }, [query.data, search]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  return (
    <>
      <PageHeader title="Applications" subtitle="Every role you've applied to" />

      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3" aria-hidden />
          <Input
            className="pl-9"
            placeholder="Search company or role…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            aria-label="Search applications"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((f) => (
            <FilterPill
              key={f.value}
              active={stage === f.value}
              onClick={() => {
                setStage(f.value);
                setPage(0);
              }}
            >
              {f.label}
            </FilterPill>
          ))}
        </div>
      </div>

      <Card className="p-0">
        {query.isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : query.isError ? (
          <div className="p-4">
            <ErrorState error={query.error} onRetry={() => query.refetch()} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title={search ? "No matching applications." : "No applications found."}
              description={
                search
                  ? "Try a different search term or clear the filter."
                  : "Promote an email or trigger a check to start your pipeline."
              }
            />
          </div>
        ) : (
          <>
            <div className="p-2">
              <Table>
                <thead>
                  <tr>
                    <Th className="pl-3">Company</Th>
                    <Th>Role</Th>
                    <Th>Status</Th>
                    <Th>Applied</Th>
                    <Th>Updated</Th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((a) => (
                    <Tr key={a.id} clickable onClick={() => navigate(`/applications/${a.id}`)}>
                      <Td className="pl-3 font-medium text-text">
                        {a.company?.name ?? "Unknown company"}
                      </Td>
                      <Td>{a.position}</Td>
                      <Td>
                        <StatusBadge stage={a.stage} />
                      </Td>
                      <Td className="font-mono text-text-3">{formatDate(a.applied_date)}</Td>
                      <Td className="font-mono text-text-3">{formatDate(a.last_updated)}</Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </div>
            <div className="flex items-center justify-between border-t border-line px-4 py-3">
              <span className="text-[12px] text-text-3">
                {filtered.length} result{filtered.length === 1 ? "" : "s"} · page {safePage + 1} of {pageCount}
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>
                  Prev
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={safePage >= pageCount - 1}
                  onClick={() => setPage(safePage + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </>
  );
}
