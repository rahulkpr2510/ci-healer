// frontend/src/components/layout/Sidebar.tsx

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  BarChart2,
  Settings,
  Cpu,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/repos", label: "Repositories", icon: GitBranch },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="flex flex-col w-56 shrink-0 h-screen sticky top-0 bg-zinc-50 dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800/60">
      {/* Logo */}
      <div className="h-[57px] flex items-center gap-2.5 px-4 border-b border-zinc-200 dark:border-zinc-800/60">
        <div className="w-7 h-7 rounded-lg bg-zinc-900 dark:bg-white flex items-center justify-center shrink-0">
          <span className="text-[11px] font-bold text-white dark:text-zinc-900">
            CI
          </span>
        </div>
        <span className="font-semibold text-zinc-900 dark:text-white text-sm tracking-tight">
          CI Healer
        </span>
        <span className="ml-auto text-[10px] font-medium text-zinc-400 dark:text-zinc-500 bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded">
          AI
        </span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            path === href ||
            path.startsWith(href + "/") ||
            (href === "/repos" && path.startsWith("/repo/"));

          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150",
                active
                  ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-medium shadow-sm"
                  : "text-zinc-500 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/60",
              ].join(" ")}
            >
              <Icon size={15} strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom — model badge */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-800/60">
        <div className="flex items-center gap-1.5">
          <Cpu size={11} className="text-zinc-400 dark:text-zinc-600" />
          <span className="text-[11px] text-zinc-400 dark:text-zinc-600">
            Gemini 2.5 Flash
          </span>
        </div>
      </div>
    </aside>
  );
}
