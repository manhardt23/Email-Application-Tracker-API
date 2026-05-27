import { useLocation, useNavigate } from "react-router-dom";

import { clearToken, getTokenRole, getValidToken } from "../lib/auth";

function pageTitle(pathname: string): string {
  if (pathname.startsWith("/applications")) {
    return "Applications";
  }
  if (pathname.startsWith("/forbidden")) {
    return "Access Restricted";
  }
  return "Dashboard";
}

export function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const token = getValidToken();
  const role = getTokenRole() ?? "viewer";
  const title = pageTitle(location.pathname);

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Overview</p>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          {role}
        </span>
        <button
          type="button"
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          onClick={() => {
            if (token) {
              clearToken();
              navigate("/login", { replace: true });
              return;
            }
            navigate("/login", { replace: true });
          }}
        >
          {token ? "Sign out" : "Sign in"}
        </button>
      </div>
    </header>
  );
}
