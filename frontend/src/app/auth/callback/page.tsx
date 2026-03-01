// frontend/src/app/auth/callback/page.tsx

"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { setToken } from "@/lib/api";

export default function AuthCallbackPage() {
  const sp = useSearchParams();
  const router = useRouter();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const token = sp.get("token");
    const error = sp.get("error");

    if (error) {
      router.replace(`/auth/login?error=${encodeURIComponent(error)}`);
      return;
    }

    if (!token) {
      router.replace("/auth/login?error=no_token");
      return;
    }

    setToken(token);
    router.replace("/dashboard");
  }, [router, sp]);

  return (
    <main className="min-h-screen bg-white dark:bg-zinc-950 flex items-center justify-center">
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
        <p className="text-xs text-zinc-400">Signing you in…</p>
      </div>
    </main>
  );
}
