import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";

import { useMe } from "../hooks/useAuth";
import { clearToken } from "../lib/auth";

export function Avatar() {
  const { data } = useMe();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const username = data?.username ?? "";
  const initial = username.slice(0, 1).toUpperCase() || "·";

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  function signOut() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="User menu"
        className="flex size-[30px] items-center justify-center rounded-full border border-line bg-sunken text-[12px] font-semibold text-text-2"
      >
        {initial}
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-[38px] w-44 rounded-md border border-line bg-surface py-1"
          style={{ boxShadow: "var(--shadow-popover)", zIndex: "var(--z-topbar)" }}
        >
          <div className="border-b border-line px-3 py-2">
            <div className="truncate text-[13px] font-medium text-text">{username || "—"}</div>
            <div className="text-[11px] text-text-3">{data?.role ?? ""}</div>
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={signOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-text-2 hover:bg-sunken"
          >
            <LogOut className="size-3.5" aria-hidden />
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
