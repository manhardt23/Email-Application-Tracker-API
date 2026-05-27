import { NavLink, useNavigate } from "react-router-dom";

import { clearToken, getValidToken } from "../lib/auth";

function navClassName(isActive: boolean): string {
  return isActive
    ? "rounded-md bg-gradient-to-r from-indigo-600 to-teal-600 px-3 py-2 text-sm font-medium text-white shadow-sm transition duration-200"
    : "rounded-md px-3 py-2 text-sm text-slate-700 transition duration-200 hover:bg-slate-100";
}

export function AppNavbar() {
  const navigate = useNavigate();
  const hasToken = Boolean(getValidToken());

  return (
    <header className="mb-6 rounded-xl border border-slate-200/80 bg-white/95 p-3 shadow-sm ring-1 ring-white backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="hidden rounded-lg bg-gradient-to-r from-indigo-600 to-teal-600 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-white sm:block">
            Jacob Manhardt
          </div>
          <nav className="flex items-center gap-2">
            <NavLink to="/" className={({ isActive }) => navClassName(isActive)}>
              Dashboard
            </NavLink>
            <NavLink to="/applications" className={({ isActive }) => navClassName(isActive)}>
              Applications
            </NavLink>
            <a href="/docs" className="rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
              Docs
            </a>
          </nav>
        </div>

        {hasToken ? (
          <button
            type="button"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 transition duration-200 hover:bg-slate-50"
            onClick={() => {
              clearToken();
              navigate("/login", { replace: true });
            }}
          >
            Sign out
          </button>
        ) : (
          <button
            type="button"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 transition duration-200 hover:bg-slate-50"
            onClick={() => navigate("/login")}
          >
            Sign in
          </button>
        )}
      </div>
    </header>
  );
}
