// frontend/src/app/auth/login/LoginPageClient.tsx

"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle } from "lucide-react";

import LoginButton from "@/components/auth/LoginButton";
import { getToken } from "@/lib/api";

export default function LoginPageClient() {
  const router = useRouter();
  const sp = useSearchParams();
  const err = sp.get("error");

  useEffect(() => {
    const token = getToken();
    if (token) router.replace("/dashboard");
  }, [router]);

  return (
    <main className="min-h-screen bg-white dark:bg-zinc-950 flex flex-col">
      {/* Top nav */}
      <nav className="flex items-center justify-between px-6 h-14 border-b border-zinc-100 dark:border-zinc-900">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-zinc-900 dark:bg-white flex items-center justify-center">
            <span className="text-[11px] font-bold text-white dark:text-zinc-900">
              CI
            </span>
          </div>
          <span className="text-sm font-semibold text-zinc-900 dark:text-white">
            CI Healer
          </span>
        </div>
      </nav>

      {/* Card */}
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-12 h-12 rounded-2xl bg-zinc-900 dark:bg-white flex items-center justify-center mx-auto mb-5">
              <span className="text-base font-bold text-white dark:text-zinc-900">
                CI
              </span>
            </div>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">
              Sign in
            </h1>
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              Connect your GitHub account to start healing CI pipelines.
            </p>
          </div>

          {/* Error */}
          {err && (
            <div className="mb-5 flex items-start gap-2.5 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3.5">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>
                Authentication failed
                {err !== "true" ? `: ${err}` : ""}. Please try again.
              </span>
            </div>
          )}

          <LoginButton />

          <p className="mt-5 text-xs text-zinc-400 dark:text-zinc-600 text-center leading-relaxed">
            By signing in, you allow CI Healer to access the repositories you
            authorize during the OAuth flow.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="px-6 py-4 text-center text-xs text-zinc-300 dark:text-zinc-700 border-t border-zinc-100 dark:border-zinc-900">
        CI Healer — Autonomous CI/CD AI DevOps Agent
      </footer>
    </main>
  );
}
