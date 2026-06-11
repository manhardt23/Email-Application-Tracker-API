import { useState } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[220px_1fr]">
      {/* Static sidebar (desktop) */}
      <aside className="hidden border-r border-line bg-surface md:block">
        <div className="sticky top-0 h-screen overflow-y-auto">
          <Sidebar />
        </div>
      </aside>

      {/* Off-canvas sidebar (mobile) */}
      {mobileOpen ? (
        <>
          <div
            className="fixed inset-0 bg-[rgba(28,25,23,0.28)] md:hidden"
            style={{ zIndex: "var(--z-backdrop)" }}
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <aside
            className="fixed left-0 top-0 h-screen w-[220px] border-r border-line bg-surface md:hidden"
            style={{ zIndex: "var(--z-drawer)" }}
          >
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </aside>
        </>
      ) : null}

      <div className="flex min-w-0 flex-col">
        <Topbar onMenu={() => setMobileOpen(true)} />
        <main className="mx-auto w-full max-w-[1080px] flex-1 px-4 py-[26px] pb-[60px] md:px-[26px]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
