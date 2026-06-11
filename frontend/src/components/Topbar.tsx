import { useLocation } from "react-router-dom";
import { Menu } from "lucide-react";

import { Avatar } from "./Avatar";
import { HealthIndicator } from "./HealthIndicator";

const TITLES: { match: (path: string) => boolean; label: string }[] = [
  { match: (p) => p === "/", label: "Dashboard" },
  { match: (p) => p.startsWith("/applications"), label: "Applications" },
  { match: (p) => p.startsWith("/emails"), label: "Emails" },
  { match: (p) => p.startsWith("/review"), label: "Review queue" },
  { match: (p) => p.startsWith("/jobs"), label: "Jobs & workers" },
];

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { pathname } = useLocation();
  const current = TITLES.find((t) => t.match(pathname))?.label ?? "App Tracker";

  return (
    <header
      className="sticky top-0 flex h-[54px] items-center justify-between border-b border-line bg-surface px-[22px]"
      style={{ zIndex: "var(--z-topbar)" }}
    >
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenu}
          aria-label="Open navigation"
          className="-ml-1 rounded-md p-1.5 text-text-2 hover:bg-sunken md:hidden"
        >
          <Menu className="size-5" aria-hidden />
        </button>
        <nav className="text-[13px] text-text-3" aria-label="Breadcrumb">
          <span className="font-semibold text-text">{current}</span>
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <div className="hidden sm:block">
          <HealthIndicator />
        </div>
        <Avatar />
      </div>
    </header>
  );
}
