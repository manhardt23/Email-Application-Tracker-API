import { NavLink, useNavigate } from "react-router-dom";

import { clearToken, getValidToken } from "../lib/auth";

function navClassName(isActive: boolean): string {
  return isActive
    ? "rounded-md bg-slate-900 px-3 py-2 text-sm text-white"
    : "rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100";
}

export function AppNavbar() {
  const navigate = useNavigate();
  const hasToken = Boolean(getValidToken());

  return (
    <header className="mb-6 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
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

        {hasToken ? (
          <button
            type="button"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
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
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => navigate("/login")}
          >
            Sign in
          </button>
        )}
      </div>
    </header>
  );
}
