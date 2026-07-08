import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Unlink } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import { ClassificationTag } from "../components/ui/ClassificationTag";
import { EmptyState } from "../components/ui/EmptyState";
import { Input, Textarea } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useToast } from "../components/ui/Toast";
import { useApplication, useApplicationEmails, useUpdateApplication } from "../hooks/useApplications";
import { useUnlinkEmail } from "../hooks/useEmails";
import { errorMessage, formatDate, formatDateTime } from "../lib/format";
import { classifyEmail, STAGE_OPTIONS, statusSwatch } from "../lib/semantic";
import type { ApplicationUpdate } from "../types/api";

export function ApplicationDetail() {
  const { id } = useParams();
  const appId = Number(id);
  const navigate = useNavigate();
  const toast = useToast();
  const query = useApplication(appId);
  const emails = useApplicationEmails(appId);
  const update = useUpdateApplication(appId);
  const unlink = useUnlinkEmail();

  const [form, setForm] = useState({ stage: "", company_name: "", position: "", notes: "" });

  const correspondenceSummary = useMemo(() => {
    const rows = emails.data ?? [];
    const counts = new Map<string, number>();
    for (const row of rows) {
      const label = classifyEmail(row).label;
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return { total: rows.length, counts: Array.from(counts.entries()) };
  }, [emails.data]);

  function handleUnlink(emailId: number) {
    unlink.mutate(emailId, {
      onSuccess: () => toast({ tone: "success", message: "Email unlinked from application." }),
      onError: (e) => toast({ tone: "error", message: errorMessage(e, "Could not unlink email.") }),
    });
  }

  useEffect(() => {
    if (query.data) {
      setForm({
        stage: query.data.stage ?? "",
        company_name: query.data.company?.name ?? "",
        position: query.data.position ?? "",
        notes: query.data.notes ?? "",
      });
    }
  }, [query.data]);

  function handleSave() {
    const original = query.data;
    if (!original) return;
    const body: ApplicationUpdate = {};
    if (form.stage !== original.stage) body.stage = form.stage;
    if (form.company_name.trim() !== (original.company?.name ?? "")) body.company_name = form.company_name.trim();
    if (form.position.trim() !== original.position) body.position = form.position.trim();
    if ((form.notes ?? "") !== (original.notes ?? "")) body.notes = form.notes;
    if (Object.keys(body).length === 0) {
      toast({ tone: "info", message: "No changes to save." });
      return;
    }
    update.mutate(body, {
      onSuccess: () => toast({ tone: "success", message: "Application updated." }),
      onError: (e) => toast({ tone: "error", message: errorMessage(e, "Update failed.") }),
    });
  }

  if (query.isLoading) {
    return (
      <>
        <PageHeader title={<Skeleton className="h-6 w-64" />} />
        <Skeleton className="h-72 w-full" />
      </>
    );
  }

  if (query.isError || !query.data) {
    return (
      <>
        <PageHeader
          title="Application"
          actions={
            <Button variant="secondary" onClick={() => navigate("/applications")}>
              <ArrowLeft className="size-3.5" /> Back
            </Button>
          }
        />
        <ErrorState error={query.error} onRetry={() => query.refetch()} fallback="Application not found." />
      </>
    );
  }

  const app = query.data;

  return (
    <>
      <PageHeader
        title={`${app.company?.name ?? "Unknown"} — ${app.position}`}
        subtitle={`Application #${app.id}`}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate("/applications")}>
              <ArrowLeft className="size-3.5" /> Back
            </Button>
            <Button variant="primary" loading={update.isPending} onClick={handleSave}>
              Save changes
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader title="Details" action={<StatusBadge stage={form.stage || app.stage} />} />
          <div className="grid grid-cols-[120px_1fr] items-center gap-x-3.5 gap-y-3 text-[13px]">
            <label className="text-text-3" htmlFor="stage">
              Status
            </label>
            <Select
              id="stage"
              value={form.stage}
              onChange={(e) => setForm((f) => ({ ...f, stage: e.target.value }))}
            >
              {STAGE_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {statusSwatch(s).label}
                </option>
              ))}
            </Select>

            <label className="text-text-3" htmlFor="company">
              Company
            </label>
            <Input
              id="company"
              value={form.company_name}
              onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
            />

            <label className="text-text-3" htmlFor="role">
              Role
            </label>
            <Input
              id="role"
              value={form.position}
              onChange={(e) => setForm((f) => ({ ...f, position: e.target.value }))}
            />

            <label className="self-start pt-2 text-text-3" htmlFor="notes">
              Notes
            </label>
            <Textarea
              id="notes"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Add context, recruiter contacts, next steps…"
            />

            <span className="text-text-3">Applied</span>
            <span className="font-mono text-text-2">{formatDate(app.applied_date)}</span>

            <span className="text-text-3">Updated</span>
            <span className="font-mono text-text-2">{formatDate(app.last_updated)}</span>
          </div>
        </Card>

        <Card>
          <CardHeader title="Linked emails" />
          {emails.isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : emails.isError ? (
            <ErrorState error={emails.error} onRetry={() => emails.refetch()} />
          ) : (emails.data?.length ?? 0) === 0 ? (
            <EmptyState
              title="No linked emails to show."
              description="Promote or link emails from the Emails tab to see them here."
            />
          ) : (
            <>
              <p className="mb-3.5 text-[12px] text-text-3">
                {correspondenceSummary.total} email{correspondenceSummary.total === 1 ? "" : "s"} —{" "}
                {correspondenceSummary.counts
                  .map(([label, count]) => `${count} ${label.toLowerCase()}`)
                  .join(", ")}
              </p>
              <ol className="relative ml-1 space-y-4 border-l border-line pl-4">
                {emails.data?.map((email) => (
                  <li key={email.id} className="relative">
                    <span
                      className="absolute -left-[21px] top-1.5 size-2 rounded-full border border-line-strong bg-surface"
                      aria-hidden
                    />
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium text-text">
                          {email.subject || "(no subject)"}
                        </p>
                        <p className="mt-0.5 font-mono text-[12px] text-text-3">
                          {email.sender} · {formatDateTime(email.received_date)}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <ClassificationTag email={email} />
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Unlink from this application"
                          aria-label="Unlink from this application"
                          onClick={() => handleUnlink(email.id)}
                        >
                          <Unlink className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </>
          )}
        </Card>
      </div>
    </>
  );
}
