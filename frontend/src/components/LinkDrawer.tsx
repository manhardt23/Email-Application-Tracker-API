import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";

import { useApplications } from "../hooks/useApplications";
import { useLinkEmail } from "../hooks/useEmails";
import { errorMessage, formatDateTime } from "../lib/format";
import type { EmailRow } from "../types/api";
import { Button } from "./ui/Button";
import { Drawer } from "./ui/Drawer";
import { EmptyState } from "./ui/EmptyState";
import { Input } from "./ui/Input";
import { Skeleton } from "./ui/Skeleton";
import { StatusBadge } from "./ui/StatusBadge";
import { useToast } from "./ui/Toast";

/** Attaches correspondence (thank-you, recruiter reply, auto-rejection, etc.)
 * to an existing application — never creates one, never touches stage. */
export function LinkDrawer({
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
  const link = useLinkEmail();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      setSearch("");
      setDebouncedSearch("");
      setSelectedId(null);
      link.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const query = useApplications("all", debouncedSearch, 0);
  const results = query.data?.items ?? [];

  function handleConfirm() {
    if (!email || selectedId === null) return;
    link.mutate(
      { emailId: email.id, body: { application_id: selectedId } },
      {
        onSuccess: (res) => {
          onClose();
          toast({
            tone: "success",
            message: "Email linked to application.",
            action: {
              label: "View application",
              onClick: () => navigate(`/applications/${res.application_id}`),
            },
          });
        },
      },
    );
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Link to application"
      context={<span className="font-mono">POST /emails/{email?.id}/link</span>}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={link.isPending}
            disabled={selectedId === null}
            onClick={handleConfirm}
          >
            Link
          </Button>
        </>
      }
    >
      {email ? (
        <div className="space-y-5">
          <div className="rounded-md border border-line bg-sunken p-3.5">
            <div className="flex items-center justify-between gap-2 text-[12px] text-text-3">
              <span className="truncate font-mono">{email.sender}</span>
              <span className="font-mono">{formatDateTime(email.received_date)}</span>
            </div>
            <p className="mt-1.5 text-[13px] font-medium text-text">
              {email.subject || "(no subject)"}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-line" />
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3">
              Attach to existing application
            </span>
            <span className="h-px flex-1 bg-line" />
          </div>

          {link.isError ? (
            <p
              role="alert"
              className="rounded-md border px-3 py-2 text-[12px]"
              style={{
                color: "var(--color-danger-fg)",
                backgroundColor: "var(--color-danger-bg)",
                borderColor: "var(--color-danger-border)",
              }}
            >
              {errorMessage(link.error, "Could not link this email.")}
            </p>
          ) : null}

          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3"
              aria-hidden
            />
            <Input
              className="pl-9"
              placeholder="Search company or role…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search applications"
              autoFocus
            />
          </div>

          <div className="max-h-[320px] space-y-1.5 overflow-auto">
            {query.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)
            ) : results.length === 0 ? (
              <EmptyState
                title="No applications found."
                description="Try a different search term."
              />
            ) : (
              results.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setSelectedId(a.id)}
                  className="flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2.5 text-left transition-colors"
                  style={{
                    borderColor: selectedId === a.id ? "var(--color-accent)" : "var(--color-line)",
                    backgroundColor: selectedId === a.id ? "var(--color-sunken)" : "transparent",
                  }}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-text">
                      {a.company?.name ?? "Unknown Company"}
                    </span>
                    <span className="block truncate text-[12px] text-text-3">{a.position}</span>
                  </span>
                  <StatusBadge stage={a.stage} />
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </Drawer>
  );
}
