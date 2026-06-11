import { NavLink } from "react-router-dom";
import {
  Briefcase,
  Cpu,
  Inbox,
  LayoutDashboard,
  Mail,
  type LucideIcon,
} from "lucide-react";

import { cn } from "../lib/utils";

type Item = { to: string; label: string; icon: LucideIcon; end?: boolean };

const PRIMARY: Item[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/applications", label: "Applications", icon: Briefcase },
  { to: "/emails", label: "Emails", icon: Mail },
  { to: "/review", label: "Review queue", icon: Inbox },
];

const ADMIN: Item[] = [{ to: "/jobs", label: "Jobs & workers", icon: Cpu }];

function NavItem({ item, onNavigate }: { item: Item; onNavigate?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] transition-colors",
          isActive
            ? "bg-inverse text-on-inverse"
            : "text-text-2 hover:bg-sunken hover:text-text",
        )
      }
    >
      <Icon className="size-[15px] shrink-0" aria-hidden />
      {item.label}
    </NavLink>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-1 px-3.5 py-[18px]">
      <div className="mb-4 flex items-center gap-2.5 px-1">
        <div
          className="flex size-[26px] items-center justify-center rounded-[5px] border-[1.5px] border-text text-[13px] font-bold text-text"
          aria-hidden
        >
          A
        </div>
        <div className="leading-tight">
          <div className="text-[14px] font-semibold text-text">App Tracker</div>
          <div className="font-mono text-[11px] text-text-3">v0.1.0</div>
        </div>
      </div>

      <nav className="flex flex-col gap-0.5">
        {PRIMARY.map((item) => (
          <NavItem key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="mt-5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3">
        Admin
      </div>
      <nav className="mt-1 flex flex-col gap-0.5">
        {ADMIN.map((item) => (
          <NavItem key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="mt-auto px-2.5 pt-4 text-[11px] text-text-3">
        Email Application Tracker
      </div>
    </div>
  );
}
