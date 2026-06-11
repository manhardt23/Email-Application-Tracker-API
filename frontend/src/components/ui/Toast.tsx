import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, X } from "lucide-react";

type ToastTone = "success" | "error" | "info";

type Toast = {
  id: number;
  message: string;
  tone: ToastTone;
  action?: { label: string; onClick: () => void };
};

type ToastInput = Omit<Toast, "id">;

const ToastContext = createContext<((t: ToastInput) => void) | null>(null);

const TONE: Record<ToastTone, { fg: string; bg: string; border: string }> = {
  success: { fg: "#15803d", bg: "#eefcf2", border: "#bbf7d0" },
  error: { fg: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
  info: { fg: "#1d4ed8", bg: "#eff4ff", border: "#bfdbfe" },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (input: ToastInput) => {
      const id = ++counter.current;
      setToasts((prev) => [...prev, { ...input, id }]);
      window.setTimeout(() => remove(id), 4000);
    },
    [remove],
  );

  return (
    <ToastContext.Provider value={push}>
      {children}
      {createPortal(
        <div
          aria-live="polite"
          className="fixed bottom-5 right-5 flex flex-col gap-2"
          style={{ zIndex: "var(--z-toast)" }}
        >
          {toasts.map((t) => {
            const tone = TONE[t.tone];
            return (
              <div
                key={t.id}
                className="flex items-center gap-2.5 rounded-md border px-3.5 py-2.5 text-[13px]"
                style={{
                  color: tone.fg,
                  backgroundColor: tone.bg,
                  borderColor: tone.border,
                  boxShadow: "var(--shadow-popover)",
                }}
              >
                {t.tone === "success" ? <CheckCircle2 className="size-4" aria-hidden /> : null}
                <span className="font-medium">{t.message}</span>
                {t.action ? (
                  <button
                    type="button"
                    onClick={() => {
                      t.action?.onClick();
                      remove(t.id);
                    }}
                    className="font-semibold underline underline-offset-2"
                  >
                    {t.action.label}
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => remove(t.id)}
                  aria-label="Dismiss"
                  className="ml-1 opacity-60 hover:opacity-100"
                >
                  <X className="size-3.5" aria-hidden />
                </button>
              </div>
            );
          })}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return useMemo(() => ctx, [ctx]);
}
