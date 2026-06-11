import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input, Textarea } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useToast } from "../components/ui/Toast";
import { useApplication, useUpdateApplication } from "../hooks/useApplications";
import { errorMessage, formatDate } from "../lib/format";
import { STAGE_OPTIONS, statusSwatch } from "../lib/semantic";
import type { ApplicationUpdate } from "../types/api";

export function ApplicationDetail() {
  const { id } = useParams();
  const appId = Number(id);
  const navigate = useNavigate();
  const toast = useToast();
  const query = useApplication(appId);
  const update = useUpdateApplication(appId);

  const [form, setForm] = useState({ stage: "", company_name: "", position: "", notes: "" });

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
          <EmptyState
            title="No linked emails to show."
            description="Email-to-application links aren't exposed by the API yet."
          />
        </Card>
      </div>
    </>
  );
}
