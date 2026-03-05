// frontend/src/app/dashboard/page.tsx

"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Wrench,
  RefreshCw,
  Play,
} from "lucide-react";

import { getDashboardSummary, getAllHistory } from "@/lib/api";
import { useAgentStore } from "@/store/agentStore";
import type { DashboardSummary, RunSummary, Repo } from "@/types/agent";

import StatCard from "@/components/ui/StatCard";
import RunStatusBadge from "@/components/ui/RunStatusBadge";
import RunModal from "@/components/run/RunModal";

export default function DashboardPage() {
  const user = useAgentStore((s) => s.user);

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, h] = await Promise.all([
        getDashboardSummary(),
        getAllHistory(1, 10),
      ]);
      setSummary(s);
      setRuns(h.runs ?? []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Create synthetic Repo from RunSummary for quick-run
  const handleQuickRun = (run: RunSummary) => {
    const syntheticRepo: Repo = {
      id: 0,
      full_name: `${run.repo_owner}/${run.repo_name}`,
      owner: run.repo_owner,
      name: run.repo_name,
      html_url: run.repo_url,
      description: null,
      private: false,
      default_branch: "main",
      updated_at: new Date().toISOString(),
      language: null,
    };
    setSelectedRepo(syntheticRepo);
  };

  return (
    <div className="space-y-6">
      {/* Run Modal */}
      {selectedRepo && (
        <RunModal repo={selectedRepo} onClose={() => setSelectedRepo(null)} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-white">
            {user ? `Welcome back, ${user.github_username}` : "Dashboard"}
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-500 mt-0.5">
            Here&apos;s an overview of your CI runs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <Link
            href="/repos"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-colors shadow-sm"
          >
            <Play size={13} />
            New Run
          </Link>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Stat cards */}
      {summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Runs"
            value={summary.total_runs ?? 0}
            icon={GitBranch}
            accent="default"
          />
          <StatCard
            label="Pass Rate"
            value={`${summary.pass_rate ?? 0}%`}
            icon={CheckCircle2}
            accent="green"
            sub={`${summary.total_runs ?? 0} runs total`}
          />
          <StatCard
            label="Fixes Applied"
            value={summary.total_fixes_applied ?? 0}
            icon={Wrench}
            accent="amber"
          />
          <StatCard
            label="Unique Repos"
            value={summary.unique_repos ?? 0}
            icon={GitBranch}
            accent="default"
            sub={summary.repos?.slice(0, 2).join(", ") || "No repos yet"}
          />
        </div>
      ) : (
        !loading && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 h-24 shimmer"
              />
            ))}
          </div>
        )
      )}

      {/* Recent runs */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
              Recent Runs
            </h2>
            <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-0.5">
              Last {runs.length} run{runs.length !== 1 ? "s" : ""} across all
              repos
            </p>
          </div>
          <Link
            href="/repos"
            className="text-xs text-zinc-400 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition-colors"
          >
            New run →
          </Link>
        </div>

        {loading ? (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="px-5 py-3.5 flex gap-3 items-center">
                <div className="h-3.5 w-3.5 shimmer rounded-full" />
                <div className="h-3.5 w-40 shimmer rounded" />
                <div className="h-3.5 w-16 shimmer rounded ml-auto" />
              </div>
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <div className="w-10 h-10 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto mb-3">
              <GitBranch size={18} className="text-zinc-400" />
            </div>
            <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
              No runs yet
            </p>
            <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-1">
              Connect a repo and trigger your first healing run.
            </p>
            <Link
              href="/repos"
              className="inline-flex items-center gap-1.5 mt-4 px-3 py-1.5 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-xs font-semibold hover:bg-zinc-700 dark:hover:bg-zinc-100 transition-colors"
            >
              <Play size={11} /> Start your first run
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {runs.map((r) => {
              const statusBar =
                r.final_status === "PASSED"
                  ? "bg-emerald-500"
                  : r.final_status === "FAILED"
                    ? "bg-red-500"
                    : r.final_status === "NO_ISSUES"
                      ? "bg-amber-400"
                      : "bg-zinc-400";

              return (
                <div
                  key={r.run_id}
                  className="relative flex items-center gap-3 px-5 py-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors group"
                >
                  {/* Status bar */}
                  <div
                    className={`absolute left-0 inset-y-0 w-0.5 ${statusBar} opacity-60 group-hover:opacity-100 transition-opacity`}
                  />

                  {/* Status icon */}
                  <Link href={`/run/${r.run_id}`} className="shrink-0 ml-2">
                    {r.final_status === "PASSED" ? (
                      <CheckCircle2 size={15} className="text-emerald-500" />
                    ) : r.final_status === "FAILED" ? (
                      <XCircle size={15} className="text-red-500" />
                    ) : r.final_status === "NO_ISSUES" ? (
                      <CheckCircle2 size={15} className="text-amber-400" />
                    ) : (
                      <RefreshCw
                        size={15}
                        className="text-zinc-400 animate-spin"
                      />
                    )}
                  </Link>

                  {/* Repo */}
                  <Link href={`/run/${r.run_id}`} className="min-w-0 flex-1">
                    <p className="text-sm text-zinc-800 dark:text-zinc-200 font-mono font-medium truncate">
                      {r.repo_owner}/{r.repo_name}
                    </p>
                    <p className="text-xs text-zinc-400 dark:text-zinc-600 truncate mt-0.5">
                      {r.started_at
                        ? new Date(r.started_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                      {r.total_time_seconds
                        ? ` · ${r.total_time_seconds < 60 ? `${r.total_time_seconds.toFixed(0)}s` : `${Math.floor(r.total_time_seconds / 60)}m ${Math.round(r.total_time_seconds % 60)}s`}`
                        : ""}
                    </p>
                  </Link>

                  {/* Stats + quick run */}
                  <div className="flex items-center gap-2 shrink-0">
                    <RunStatusBadge status={r.final_status} />
                    <span className="text-xs text-zinc-400 dark:text-zinc-500 hidden sm:block tabular-nums">
                      {r.total_fixes_applied} fix
                      {r.total_fixes_applied !== 1 ? "es" : ""}
                    </span>
                    <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400 hidden sm:block bg-zinc-50 dark:bg-zinc-800 px-1.5 py-0.5 rounded font-semibold tabular-nums">
                      {r.final_score ?? "—"} pts
                    </span>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleQuickRun(r);
                      }}
                      className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all"
                      title="Re-run this repo"
                    >
                      <Play size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
