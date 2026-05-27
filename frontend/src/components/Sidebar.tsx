import { BookOpen, Globe, LayoutDashboard, Mail } from "lucide-react";
import { NavLink } from "react-router-dom";

function navItemClassName(isActive: boolean): string {
  return isActive
    ? "flex items-center gap-3 rounded-lg bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 transition"
    : "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100";
}

export function Sidebar() {
  return (
    <aside className="sticky top-0 h-screen w-60 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4 shadow-sm">
      <div className="rounded-xl bg-gradient-to-r from-indigo-600 to-teal-600 px-3 py-3 text-white">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-100">Email Tracker</p>
        <p className="mt-1 text-sm font-semibold">Portfolio Dashboard</p>
      </div>

      <nav className="mt-6 space-y-6">
        <section className="space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Main</p>
          <NavLink to="/" end className={({ isActive }) => navItemClassName(isActive)}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>
          <NavLink to="/applications" className={({ isActive }) => navItemClassName(isActive)}>
            <Mail className="h-4 w-4" />
            Applications
          </NavLink>
        </section>

        <section className="space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Resources</p>
          <a
            href="/docs"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100"
          >
            <BookOpen className="h-4 w-4" />
            API Docs
          </a>
          <a
            href="https://github.com/manhardt23"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100"
          >
            <Globe className="h-4 w-4" />
            GitHub
          </a>
        </section>
      </nav>
    </aside>
  );
}
