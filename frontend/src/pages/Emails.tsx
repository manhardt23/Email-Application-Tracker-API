import { useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { PromoteDrawer } from "../components/PromoteDrawer";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ClassificationTag } from "../components/ui/ClassificationTag";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPill } from "../components/ui/FilterPill";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { Table, Td, Th, Tr } from "../components/ui/Table";
import { EMAILS_PAGE_SIZE, useEmails } from "../hooks/useEmails";
import { formatDateTime } from "../lib/format";
import { classifyEmail } from "../lib/semantic";
import type { EmailRow } from "../types/api";

const CLASS_FILTERS = [
  { value: "all", label: "All" },
  { value: "Interview invite", label: "Interview invite" },
  { value: "Acknowledgement", label: "Acknowledgement" },
  { value: "Offer", label: "Offer" },
  { value: "Rejection", label: "Rejection" },
  { value: "Needs review", label: "Needs review" },
  { value: "Not relevant", label: "Not relevant" },
];

export function Emails() {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("all");
  const [promoteEmail, setPromoteEmail] = useState<EmailRow | null>(null);
  const query = useEmails(offset);

  const filtered = useMemo(() => {
    const rows = query.data ?? [];
    const term = search.trim().toLowerCase();
    return rows.filter((e) => {
      const matchesSearch =
        !term ||
        e.sender.toLowerCase().includes(term) ||
        (e.subject ?? "").toLowerCase().includes(term);
      const matchesClass = classFilter === "all" || classifyEmail(e).label === classFilter;
      return matchesSearch && matchesClass;
    });
  }, [query.data, search, classFilter]);

  const pageFull = (query.data?.length ?? 0) === EMAILS_PAGE_SIZE;

  return (
    <>
      <PageHeader title="Emails" subtitle="All ingested & classified messages" />

      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3" aria-hidden />
          <Input
            className="pl-9"
            placeholder="Search sender or subject…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search emails"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {CLASS_FILTERS.map((f) => (
            <FilterPill key={f.value} active={classFilter === f.value} onClick={() => setClassFilter(f.value)}>
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
              title={query.data && query.data.length > 0 ? "No emails match these filters." : "No emails ingested yet."}
              description={
                query.data && query.data.length > 0
                  ? "Adjust search or classification filters."
                  : "Trigger an email check from Jobs & workers to ingest messages."
              }
            />
          </div>
        ) : (
          <>
            <div className="p-2">
              <Table>
                <thead>
                  <tr>
                    <Th className="pl-3">From</Th>
                    <Th>Subject</Th>
                    <Th>Classification</Th>
                    <Th>Received</Th>
                    <Th className="text-right">Action</Th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((e) => (
                    <Tr key={e.id}>
                      <Td className="pl-3 font-mono text-[12px] text-text">{e.sender}</Td>
                      <Td className="max-w-[280px] truncate text-text">{e.subject || "(no subject)"}</Td>
                      <Td>
                        <ClassificationTag email={e} />
                      </Td>
                      <Td className="font-mono text-text-3">{formatDateTime(e.received_date)}</Td>
                      <Td className="text-right">
                        <Button size="sm" variant="secondary" onClick={() => setPromoteEmail(e)}>
                          Promote <ArrowRight className="size-3.5" />
                        </Button>
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </div>
            <div className="flex items-center justify-between border-t border-line px-4 py-3">
              <span className="text-[12px] text-text-3">
                Showing {filtered.length} of this page · offset {offset}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - EMAILS_PAGE_SIZE))}
                >
                  Prev
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!pageFull}
                  onClick={() => setOffset(offset + EMAILS_PAGE_SIZE)}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>

      <PromoteDrawer email={promoteEmail} open={promoteEmail !== null} onClose={() => setPromoteEmail(null)} />
    </>
  );
}
