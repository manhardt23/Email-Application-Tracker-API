import { useState } from "react";
import { RefreshCw } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { MetricCard } from "../components/ui/MetricCard";
import { Table, Td, Th, Tr } from "../components/ui/Table";
import { useToast } from "../components/ui/Toast";
import {
  isTerminalStatus,
  useJobStatus,
  useSetEmailLimit,
  useStats,
  useTriggerBackfill,
  useTriggerEmailCheck,
} from "../hooks/useJobs";
import { errorMessage, formatDateTime, formatRelative } from "../lib/format";

export function JobsAdmin() {
  const toast = useToast();
  const [jobIds, setJobIds] = useState<string[]>([]);
  const check = useTriggerEmailCheck();
  const backfill = useTriggerBackfill();
  const setLimit = useSetEmailLimit();
  const stats = useStats();

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [backfillMax, setBackfillMax] = useState("");
  const [limit, setLimitValue] = useState("");

  function trackJob(id: string) {
    setJobIds((prev) => (prev.includes(id) ? prev : [id, ...prev]));
  }

  function runCheck() {
    check.mutate(undefined, {
      onSuccess: (r) => {
        trackJob(r.job_id);
        toast({ tone: "success", message: `Email check queued (#${r.job_id}).` });
      },
      onError: (e) => toast({ tone: "error", message: errorMessage(e, "Could not start check.") }),
    });
  }

  function runBackfill() {
    if (!fromDate) {
      toast({ tone: "error", message: "Choose a start date for the backfill." });
      return;
    }
    backfill.mutate(
      {
        from_date: new Date(fromDate).toISOString(),
        to_date: toDate ? new Date(toDate).toISOString() : undefined,
        max_emails: backfillMax ? Number(backfillMax) : undefined,
      },
      {
        onSuccess: (r) => {
          trackJob(r.job_id);
          toast({ tone: "success", message: `Backfill queued (#${r.job_id}).` });
        },
        onError: (e) => toast({ tone: "error", message: errorMessage(e, "Could not start backfill.") }),
      },
    );
  }

  function runLimit() {
    const value = Number(limit);
    if (!value || value < 1) {
      toast({ tone: "error", message: "Enter a limit of 1 or more." });
      return;
    }
    setLimit.mutate(value, {
      onSuccess: (r) => toast({ tone: "success", message: `Worker limit set to ${r.max_emails_per_run}.` }),
      onError: (e) => toast({ tone: "error", message: errorMessage(e, "Could not set limit.") }),
    });
  }

  return (
    <>
      <PageHeader title="Jobs & workers" subtitle="Trigger ingestion runs and tune the worker" />

      <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
        <Card>
          <CardHeader title="Check for new email" />
          <p className="mb-3 text-[12px] text-text-3">Run an incremental fetch for recent messages.</p>
          <Button variant="primary" loading={check.isPending} onClick={runCheck}>
            Run check
          </Button>
        </Card>

        <Card>
          <CardHeader title="Backfill history" />
          <div className="space-y-2">
            <label className="block text-[12px] text-text-3">
              From
              <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="mt-1" />
            </label>
            <label className="block text-[12px] text-text-3">
              To (optional)
              <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="mt-1" />
            </label>
            <label className="block text-[12px] text-text-3">
              Max emails (optional)
              <Input
                type="number"
                min={1}
                max={1000}
                value={backfillMax}
                onChange={(e) => setBackfillMax(e.target.value)}
                className="mt-1"
              />
            </label>
            <Button variant="secondary" loading={backfill.isPending} onClick={runBackfill}>
              Run backfill
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader title="Worker email limit" />
          <p className="mb-3 text-[12px] text-text-3">Max emails processed per worker run.</p>
          <div className="flex items-end gap-2">
            <label className="block flex-1 text-[12px] text-text-3">
              Limit
              <Input
                type="number"
                min={1}
                max={1000}
                value={limit}
                onChange={(e) => setLimitValue(e.target.value)}
                className="mt-1"
              />
            </label>
            <Button variant="secondary" loading={setLimit.isPending} onClick={runLimit}>
              Apply
            </Button>
          </div>
        </Card>
      </div>

      <div className="mt-3.5 grid grid-cols-1 gap-3.5 lg:grid-cols-2">
        <Card className="p-0">
          <div className="p-4">
            <CardHeader title="Jobs this session" />
          </div>
          {jobIds.length === 0 ? (
            <div className="px-4 pb-4">
              <EmptyState
                title="No jobs triggered yet."
                description="Jobs you start in this session appear here and poll until they finish."
              />
            </div>
          ) : (
            <div className="px-2 pb-2">
              <Table>
                <thead>
                  <tr>
                    <Th className="pl-3">Job</Th>
                    <Th>Status</Th>
                    <Th>Fetched</Th>
                    <Th>Saved</Th>
                    <Th>Apps</Th>
                    <Th>Finished</Th>
                  </tr>
                </thead>
                <tbody>
                  {jobIds.map((id) => (
                    <JobRow key={id} jobId={id} />
                  ))}
                </tbody>
              </Table>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            title="System stats"
            action={
              <Button size="sm" variant="ghost" onClick={() => stats.refetch()} aria-label="Refresh stats">
                <RefreshCw className="size-3.5" />
              </Button>
            }
          />
          {stats.isError ? (
            <ErrorState error={stats.error} onRetry={() => stats.refetch()} />
          ) : (
            <div className="grid grid-cols-2 gap-3.5">
              <MetricCard
                label="Emails processed"
                value={stats.data?.total_emails_processed ?? 0}
                loading={stats.isLoading}
              />
              <MetricCard
                label="Job-related"
                value={stats.data?.job_related_emails ?? 0}
                loading={stats.isLoading}
              />
              <MetricCard
                label="Worker runs (7d)"
                value={stats.data?.worker_run_count_7d ?? 0}
                loading={stats.isLoading}
              />
              <MetricCard
                label="Last run"
                value={stats.isLoading ? "…" : formatRelative(stats.data?.worker_last_ran_at)}
                loading={stats.isLoading}
              />
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

function JobRow({ jobId }: { jobId: string }) {
  const { data, isLoading, isError } = useJobStatus(jobId);
  const status = data?.status ?? (isError ? "error" : "queued");
  const running = !isTerminalStatus(status);

  return (
    <Tr>
      <Td className="pl-3 font-mono text-text">#{jobId}</Td>
      <Td>
        <span className="inline-flex items-center gap-1.5 text-[12px] text-text-2">
          {running ? (
            <span className="inline-block size-2 animate-pulse rounded-full bg-accent" aria-hidden />
          ) : null}
          {isLoading ? "loading…" : status}
        </span>
      </Td>
      <Td className="font-mono">{data?.emails_fetched ?? "—"}</Td>
      <Td className="font-mono">{data?.emails_saved ?? "—"}</Td>
      <Td className="font-mono">{data?.applications_found ?? "—"}</Td>
      <Td className="font-mono text-text-3">{data?.finished_at ? formatDateTime(data.finished_at) : "—"}</Td>
    </Tr>
  );
}
