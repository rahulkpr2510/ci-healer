// frontend/src/components/layout/Sidebar.tsx

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  BarChart2,
  Settings,
  Zap,
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
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-600 to-violet-800 flex items-center justify-center shrink-0 shadow-sm shadow-violet-500/30">
          <Zap size={13} className="text-white" />
        </div>
        <span className="font-semibold text-zinc-900 dark:text-white text-sm tracking-tight">
          CI Healer
        </span>
        <span className="ml-auto text-[10px] font-semibold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20 px-1.5 py-0.5 rounded">
          AI
        </span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            path === href ||
            path.startsWith(href + "/") ||
            (href === "/repos" && path.startsWith("/repo/")) ||
            (href === "/dashboard" && path.startsWith("/run/"));

          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150",
                active
                  ? "bg-violet-600 text-white font-medium shadow-sm shadow-violet-500/20"
                  : "text-zinc-500 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/60",
              ].join(" ")}
            >
              <Icon size={15} strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-800/60">
        <p className="text-[10px] text-zinc-400 dark:text-zinc-600 text-center">
          AI-powered CI/CD healing
        </p>
      </div>
    </aside>
  );
}
