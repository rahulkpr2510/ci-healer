// frontend/src/components/auth/AuthGuard.tsx

"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { getMe, clearToken, getToken } from "@/lib/api";
import { useAgentStore } from "@/store/agentStore";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const user = useAgentStore((s) => s.user);
  const authLoading = useAgentStore((s) => s.authLoading);
  const setUser = useAgentStore((s) => s.setUser);
  const setAuthLoading = useAgentStore((s) => s.setAuthLoading);

  useEffect(() => {
    let mounted = true;

    const PROTECTED = [
      "/dashboard",
      "/repos",
      "/repo",
      "/analytics",
      "/settings",
      "/run",
    ];
    const isProtected = PROTECTED.some((p) => pathname.startsWith(p));

    async function boot() {
      const token = getToken();

      if (!token) {
        if (isProtected) router.replace("/auth/login");
        if (mounted) setAuthLoading(false);
        return;
      }

      try {
        const me = await getMe();
        if (!mounted) return;
        setUser(me);
      } catch {
        clearToken();
        if (!mounted) return;
        setUser(null);
        if (isProtected) router.replace("/auth/login");
      } finally {
        if (mounted) setAuthLoading(false);
      }
    }

    if (!user) boot();
    else setAuthLoading(false);

    return () => {
      mounted = false;
    };
  }, [pathname, router, setAuthLoading, setUser, user]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-white dark:bg-zinc-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-zinc-900 dark:bg-white flex items-center justify-center">
            <span className="text-[11px] font-bold text-white dark:text-zinc-900">
              CI
            </span>
          </div>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700 animate-pulse"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
