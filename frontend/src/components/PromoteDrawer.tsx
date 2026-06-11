import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { usePromoteEmail } from "../hooks/useEmails";
import { errorMessage, formatDateTime } from "../lib/format";
import { STAGE_OPTIONS, statusSwatch } from "../lib/semantic";
import type { EmailRow } from "../types/api";
import { Button } from "./ui/Button";
import { Drawer } from "./ui/Drawer";
import { Input } from "./ui/Input";
import { Select } from "./ui/Select";
import { useToast } from "./ui/Toast";

export function PromoteDrawer({
  email,
  open,
  onClose,
}: {
  email: EmailRow | null;
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const promote = usePromoteEmail();
  const [form, setForm] = useState({ company_name: "", position: "", stage: "applied" });

  useEffect(() => {
    if (email) {
      setForm({
        company_name: email.detected_company ?? "",
        position: email.detected_position ?? "",
        stage: (email.detected_stage ?? "applied").toLowerCase(),
      });
      promote.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email]);

  function handleConfirm() {
    if (!email) return;
    promote.mutate(
      {
        emailId: email.id,
        body: {
          company_name: form.company_name.trim() || undefined,
          position: form.position.trim() || undefined,
          stage: form.stage || undefined,
        },
      },
      {
        onSuccess: (res) => {
          onClose();
          toast({
            tone: "success",
            message: res.created ? "Application created." : "Email linked to application.",
            action: {
              label: "View application",
              onClick: () => navigate(`/applications/${res.application_id}`),
            },
          });
        },
      },
    );
  }

  const stageOptions = STAGE_OPTIONS.includes(form.stage as (typeof STAGE_OPTIONS)[number])
    ? STAGE_OPTIONS
    : [form.stage, ...STAGE_OPTIONS];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Promote to application"
      context={<span className="font-mono">POST /emails/{email?.id}/promote</span>}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" loading={promote.isPending} onClick={handleConfirm}>
            Promote
          </Button>
        </>
      }
    >
      {email ? (
        <div className="space-y-5">
          {/* Source email preview */}
          <div className="rounded-md border border-line bg-sunken p-3.5">
            <div className="flex items-center justify-between gap-2 text-[12px] text-text-3">
              <span className="truncate font-mono">{email.sender}</span>
              <span className="font-mono">{formatDateTime(email.received_date)}</span>
            </div>
            <p className="mt-1.5 text-[13px] font-medium text-text">
              {email.subject || "(no subject)"}
            </p>
          </div>

          {/* Labeled divider */}
          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-line" />
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3">
              Creates application
            </span>
            <span className="h-px flex-1 bg-line" />
          </div>

          {promote.isError ? (
            <p
              role="alert"
              className="rounded-md border px-3 py-2 text-[12px]"
              style={{
                color: "var(--color-danger-fg)",
                backgroundColor: "var(--color-danger-bg)",
                borderColor: "var(--color-danger-border)",
              }}
            >
              {errorMessage(promote.error, "Could not promote this email.")}
            </p>
          ) : null}

          <div className="grid grid-cols-[100px_1fr] items-center gap-x-3.5 gap-y-3 text-[13px]">
            <label className="text-text-3" htmlFor="p-company">
              Company
            </label>
            <Input
              id="p-company"
              value={form.company_name}
              onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
              placeholder="Unknown Company"
            />
            <label className="text-text-3" htmlFor="p-role">
              Role
            </label>
            <Input
              id="p-role"
              value={form.position}
              onChange={(e) => setForm((f) => ({ ...f, position: e.target.value }))}
              placeholder="Unknown Position"
            />
            <label className="text-text-3" htmlFor="p-stage">
              Status
            </label>
            <Select
              id="p-stage"
              value={form.stage}
              onChange={(e) => setForm((f) => ({ ...f, stage: e.target.value }))}
            >
              {stageOptions.map((s) => (
                <option key={s} value={s}>
                  {statusSwatch(s).label}
                </option>
              ))}
            </Select>
          </div>

          <p className="text-[12px] text-text-3">Fields are editable before promoting.</p>
        </div>
      ) : null}
    </Drawer>
  );
}
