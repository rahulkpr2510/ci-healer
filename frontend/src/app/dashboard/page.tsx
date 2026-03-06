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
  Clock,
  TrendingUp,
  BarChart2,
  ArrowRight,
  List,
} from "lucide-react";

import { getDashboardSummary, getAllHistory } from "@/lib/api";
import { useAgentStore } from "@/store/agentStore";
import type { DashboardSummary, RunSummary, Repo } from "@/types/agent";

import StatCard from "@/components/ui/StatCard";
import RunStatusBadge from "@/components/ui/RunStatusBadge";
import RunModal from "@/components/run/RunModal";

const PAGE_SIZE = 15;

export default function DashboardPage() {
  const user = useAgentStore((s) => s.user);

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [showAll, setShowAll] = useState(false);

  const load = useCallback(async (reset = true) => {
    if (reset) setLoading(true);
    setError(null);
    try {
      const [s, h] = await Promise.all([
        getDashboardSummary(),
        getAllHistory(1, PAGE_SIZE),
      ]);
      setSummary(s);
      setRuns(h.runs ?? []);
      setTotalRuns(s.total_runs ?? 0);
      setPage(1);
      setShowAll(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const h = await getAllHistory(nextPage, PAGE_SIZE);
      setRuns((prev) => [...prev, ...(h.runs ?? [])]);
      setPage(nextPage);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }, [page]);

  const loadAll = useCallback(async () => {
    setLoadingMore(true);
    try {
      const h = await getAllHistory(1, 200);
      setRuns(h.runs ?? []);
      setShowAll(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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

  const passedRuns = runs.filter((r) => r.final_status === "PASSED").length;
  const failedRuns = runs.filter((r) => r.final_status === "FAILED").length;

  return (
    <div className="space-y-6">
      {selectedRepo && (
        <RunModal repo={selectedRepo} onClose={() => setSelectedRepo(null)} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-white">
            {user ? `Welcome back, ${user.github_username} 👋` : "Dashboard"}
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-500 mt-0.5">
            Overview of your CI healing activity
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => load()}
            disabled={loading}
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

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 h-24 shimmer"
            />
          ))}
        </div>
      ) : summary ? (
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
            icon={TrendingUp}
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
            label="Repositories"
            value={summary.unique_repos ?? 0}
            icon={BarChart2}
            accent="default"
            sub={summary.repos?.slice(0, 2).join(", ") || "None yet"}
          />
        </div>
      ) : null}

      {/* Quick stats bar */}
      {!loading && runs.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {[
            {
              label: "Passed",
              count: passedRuns,
              color: "text-emerald-500",
              bg: "bg-emerald-500/8 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20",
            },
            {
              label: "Failed",
              count: failedRuns,
              color: "text-red-500",
              bg: "bg-red-500/8 dark:bg-red-500/10 border-red-200 dark:border-red-500/20",
            },
            {
              label: "Avg Time",
              count: null,
              color: "text-zinc-500",
              bg: "bg-zinc-50 dark:bg-zinc-800/40 border-zinc-200 dark:border-zinc-700",
            },
          ].map(({ label, count, color, bg }) => {
            const avgTime =
              runs.reduce((acc, r) => acc + (r.total_time_seconds ?? 0), 0) /
              (runs.filter((r) => r.total_time_seconds).length || 1);
            const display =
              count !== null
                ? count
                : avgTime < 60
                  ? `${avgTime.toFixed(0)}s`
                  : `${Math.floor(avgTime / 60)}m`;
            return (
              <div
                key={label}
                className={`flex items-center justify-between px-4 py-3 rounded-xl border ${bg}`}
              >
                <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  {label}
                </span>
                <span className={`text-lg font-bold tabular-nums ${color}`}>
                  {display}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Recent runs */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
              {showAll ? "All Runs" : "Recent Runs"}
            </h2>
            <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-0.5">
              {runs.length} of {totalRuns} total run{totalRuns !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!showAll && totalRuns > runs.length && (
              <button
                onClick={loadAll}
                disabled={loadingMore}
                className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800"
              >
                <List size={11} />
                {loadingMore ? "Loading…" : `View all ${totalRuns}`}
              </button>
            )}
            <Link
              href="/analytics"
              className="flex items-center gap-1 text-xs text-zinc-400 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition-colors"
            >
              Analytics <ArrowRight size={11} />
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-5 py-3.5 flex gap-3 items-center">
                <div className="h-3.5 w-3.5 shimmer rounded-full" />
                <div className="h-3.5 w-48 shimmer rounded" />
                <div className="h-3.5 w-16 shimmer rounded ml-auto" />
              </div>
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="px-5 py-16 text-center">
            <div className="w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto mb-4">
              <GitBranch size={20} className="text-zinc-400" />
            </div>
            <p className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
              No runs yet
            </p>
            <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-1 max-w-xs mx-auto">
              Connect a repository and trigger your first AI-powered healing
              run.
            </p>
            <Link
              href="/repos"
              className="inline-flex items-center gap-1.5 mt-4 px-4 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-xs font-semibold hover:bg-zinc-700 dark:hover:bg-zinc-100 transition-colors"
            >
              <Play size={11} /> Start your first run
            </Link>
          </div>
        ) : (
          <>
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {runs.map((r) => {
                const statusBarCls =
                  r.final_status === "PASSED"
                    ? "bg-emerald-500"
                    : r.final_status === "FAILED"
                      ? "bg-red-500"
                      : r.final_status === "NO_ISSUES"
                        ? "bg-amber-400"
                        : "bg-violet-500";

                const isRunning = r.final_status === "RUNNING";

                return (
                  <div
                    key={r.run_id}
                    className="relative flex items-center gap-3 px-5 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors group"
                  >
                    <div
                      className={`absolute left-0 inset-y-0 w-0.5 ${statusBarCls} opacity-50 group-hover:opacity-100 transition-opacity`}
                    />

                    {/* Icon */}
                    <Link href={`/run/${r.run_id}`} className="shrink-0 ml-2">
                      {r.final_status === "PASSED" ? (
                        <CheckCircle2 size={14} className="text-emerald-500" />
                      ) : r.final_status === "FAILED" ? (
                        <XCircle size={14} className="text-red-500" />
                      ) : r.final_status === "NO_ISSUES" ? (
                        <CheckCircle2 size={14} className="text-amber-400" />
                      ) : (
                        <RefreshCw
                          size={14}
                          className="text-violet-500 animate-spin"
                        />
                      )}
                    </Link>

                    {/* Repo + date */}
                    <Link href={`/run/${r.run_id}`} className="min-w-0 flex-1">
                      <p className="text-sm text-zinc-800 dark:text-zinc-200 font-medium font-mono truncate">
                        {r.repo_owner}/{r.repo_name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {r.started_at && (
                          <span className="text-xs text-zinc-400 dark:text-zinc-600">
                            {new Date(r.started_at).toLocaleString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                        {r.total_time_seconds && (
                          <span className="flex items-center gap-0.5 text-xs text-zinc-400 dark:text-zinc-600">
                            <Clock size={10} />
                            {r.total_time_seconds < 60
                              ? `${r.total_time_seconds.toFixed(0)}s`
                              : `${Math.floor(r.total_time_seconds / 60)}m ${Math.round(r.total_time_seconds % 60)}s`}
                          </span>
                        )}
                      </div>
                    </Link>

                    {/* Right side stats */}
                    <div className="flex items-center gap-2 shrink-0">
                      {/* Error/fix badges */}
                      {(r.total_failures_detected ?? 0) > 0 && (
                        <span className="hidden sm:flex items-center gap-0.5 text-[10px] font-medium text-red-500 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 px-1.5 py-0.5 rounded-full">
                          <XCircle size={9} /> {r.total_failures_detected} err
                        </span>
                      )}
                      {r.total_fixes_applied > 0 && (
                        <span className="hidden sm:flex items-center gap-0.5 text-[10px] font-medium text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 px-1.5 py-0.5 rounded-full">
                          <Wrench size={9} /> {r.total_fixes_applied} fix
                          {r.total_fixes_applied !== 1 ? "es" : ""}
                        </span>
                      )}
                      <RunStatusBadge status={r.final_status} />
                      {!isRunning && (
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleQuickRun(r);
                          }}
                          className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all"
                          title="Re-run this repo"
                        >
                          <Play size={11} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Load more */}
            {!showAll && runs.length < totalRuns && (
              <div className="px-5 py-3 border-t border-zinc-100 dark:border-zinc-800/60 flex items-center justify-between">
                <span className="text-xs text-zinc-400 dark:text-zinc-500">
                  Showing {runs.length} of {totalRuns} runs
                </span>
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="text-xs text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors font-medium"
                >
                  {loadingMore ? "Loading…" : "Load more →"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
