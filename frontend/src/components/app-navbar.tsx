import { NavLink, useNavigate } from "react-router-dom";

import { clearToken, getTokenRole } from "../lib/auth";

function navClassName(isActive: boolean): string {
  return isActive
    ? "rounded-md bg-slate-900 px-3 py-2 text-sm text-white"
    : "rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100";
}

export function AppNavbar() {
  const navigate = useNavigate();
  const isAdmin = getTokenRole() === "admin";

  return (
    <header className="mb-6 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex items-center gap-2">
          <NavLink to="/" className={({ isActive }) => navClassName(isActive)}>
            Dashboard
          </NavLink>
          {isAdmin ? (
            <NavLink to="/applications" className={({ isActive }) => navClassName(isActive)}>
              Applications
            </NavLink>
          ) : null}
        </nav>

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
      </div>
    </header>
  );
}
