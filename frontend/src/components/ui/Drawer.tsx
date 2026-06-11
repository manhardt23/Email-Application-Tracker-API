import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { Button } from "./Button";

export function Drawer({
  open,
  onClose,
  title,
  context,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  context?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    triggerRef.current = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") trapFocus(e, panelRef.current);
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    // Focus first focusable inside the panel.
    requestAnimationFrame(() => {
      const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE);
      first?.focus();
    });
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      triggerRef.current?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-[rgba(28,25,23,0.28)]"
        style={{ zIndex: "var(--z-backdrop)" }}
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="fixed right-0 top-0 flex h-screen w-[440px] max-w-[92vw] flex-col border-l border-line bg-surface"
        style={{ zIndex: "var(--z-drawer)", boxShadow: "var(--shadow-drawer)" }}
      >
        <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-[18px]">
          <div>
            <h2 className="text-[16px] font-semibold text-text">{title}</h2>
            {context ? <div className="mt-0.5 text-[12px] text-text-3">{context}</div> : null}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close" className="px-1.5">
            <X className="size-4" aria-hidden />
          </Button>
        </header>
        <div className="flex-1 overflow-auto px-5 py-5">{children}</div>
        {footer ? (
          <footer className="flex items-center justify-end gap-2 border-t border-line px-5 py-3.5">
            {footer}
          </footer>
        ) : null}
      </div>
    </>,
    document.body,
  );
}

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function trapFocus(e: KeyboardEvent, container: HTMLElement | null) {
  if (!container) return;
  const nodes = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (n) => n.offsetParent !== null,
  );
  if (nodes.length === 0) return;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  const active = document.activeElement as HTMLElement | null;
  if (e.shiftKey && active === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && active === last) {
    e.preventDefault();
    first.focus();
  }
}
