import type { ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import { clearToken, getTokenRole, getValidToken } from "../lib/auth";

type AppShellProps = {
  children: ReactNode;
};

function navClassName(isActive: boolean): string {
  return isActive
    ? "flex items-center gap-2 rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700"
    : "flex items-center gap-2 rounded-lg border border-transparent px-3 py-2 text-sm text-slate-600 transition hover:border-slate-200 hover:bg-slate-50";
}

function sectionTitle(pathname: string): string {
  if (pathname.startsWith("/applications")) {
    return "Applications";
  }
  if (pathname.startsWith("/forbidden")) {
    return "Access Restricted";
  }
  return "Dashboard";
}

export function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const role = getTokenRole();
  const hasToken = Boolean(getValidToken());
  const title = sectionTitle(location.pathname);

  return (
    <div className="flex min-h-screen bg-slate-100">
      <aside className="w-60 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4 shadow-sm">
        {/* logo block */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Email Tracker</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">Portfolio Dashboard</p>
        </div>

        {/* nav sections */}
        <nav className="mt-6 space-y-6">
          <div className="space-y-1">
            <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Menu</p>
            <NavLink to="/" end className={({ isActive }) => navClassName(isActive)}>
              <span className="h-2 w-2 rounded-full bg-indigo-500" />
              Dashboard
            </NavLink>
            <NavLink to="/applications" className={({ isActive }) => navClassName(isActive)}>
              <span className="h-2 w-2 rounded-full bg-teal-500" />
              Applications
            </NavLink>
          </div>
  
          <div className="space-y-1">
            <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Resources</p>
            <a href="/docs" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">
              <span className="h-2 w-2 rounded-full bg-slate-400" />
              API Docs
            </a>
          </div>
        </nav>
      </aside>

      <div className="min-h-screen min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-400">Workspace</p>
            <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
          </div>
          <div className="flex items-center gap-2">
            {hasToken ? (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                {role ?? "user"}
              </span>
            ) : null}
            <button
              type="button"
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-50"
              onClick={() => {
                clearToken();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="space-y-6 p-8">
          {children}
        </main>
      </div>
    </div>
  );
}