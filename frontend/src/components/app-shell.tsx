import type { ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import { clearToken, getTokenRole, getValidToken } from "../lib/auth";

type AppShellProps = {
  children: ReactNode;
};

function navClassName(isActive: boolean): string {
  return isActive
    ? "flex items-center gap-2 rounded-lg bg-indigo-100 px-3 py-2 text-sm font-medium text-indigo-700"
    : "flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100";
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

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-56 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4 shadow-sm">
        {/* logo block */}
        <div className="rounded-xl bg-gradient-to-r from-indigo-600 to-teal-600 px-3 py-2 text-white">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-100">Email Tracker</p>
          <p className="mt-1 text-sm font-semibold">Portfolio Dashboard</p>
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
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-6 py-3 backdrop-blur">
          {/* your header content */}
        </header>
  
        <main className="space-y-4 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}