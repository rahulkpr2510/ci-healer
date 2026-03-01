// frontend/src/app/repo/[...repoId]/page.tsx
// Route: /repo/[owner]/[repoName]
// Shows run history for a specific GitHub repo + "Run Agent" button.

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Play,
  GitBranch,
  Clock,
  Zap,
  ExternalLink,
  BarChart3,
} from "lucide-react";

import { getRepoHistory, getRepoAnalytics } from "@/lib/api";
import type { RunSummary, RepoAnalytics, Repo } from "@/types/agent";
import RunModal from "@/components/run/RunModal";
import RunStatusBadge from "@/components/ui/RunStatusBadge";

function fmt(secs: number | null | undefined): string {
  if (!secs) return "—";
  if (secs < 60) return `${secs.toFixed(0)}s`;
  return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`;
}

export default function RepoDetailPage() {
  const params = useParams<{ repoId: string[] }>();
  const router = useRouter();

  // repoId is a catch-all segment: ['owner', 'reponame']
  const segments = params.repoId ?? [];
  const owner = segments[0] ?? "";
  const repoName = segments[1] ?? "";
  const fullName = `${owner}/${repoName}`;

  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [analytics, setAnalytics] = useState<RepoAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRunModal, setShowRunModal] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 15;

  const syntheticRepo: Repo = {
    id: 0,
    full_name: fullName,
    owner,
    name: repoName,
    html_url: `https://github.com/${fullName}`,
    description: null,
    private: false,
    default_branch: "main",
    updated_at: new Date().toISOString(),
    language: null,
  };

  const load = useCallback(async () => {
    if (!owner || !repoName) return;
    setLoading(true);
    setError(null);
    try {
      const [historyData, analyticsData] = await Promise.allSettled([
        getRepoHistory(owner, repoName, page, PAGE_SIZE),
        getRepoAnalytics(owner, repoName),
      ]);

      if (historyData.status === "fulfilled") {
        setRuns(historyData.value.runs ?? []);
      }
      if (analyticsData.status === "fulfilled") {
        setAnalytics(analyticsData.value);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [owner, repoName, page]);

  useEffect(() => {
    load();
  }, [load]);

  const latestRun = runs[0];

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Run Modal */}
      {showRunModal && (
        <RunModal repo={syntheticRepo} onClose={() => setShowRunModal(false)} />
      )}

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-start gap-3">
          <button
            onClick={() => router.push("/repos")}
            className="mt-1 p-1.5 rounded-lg text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-zinc-900 dark:text-white font-mono">
                {fullName}
              </h1>
              {latestRun && <RunStatusBadge status={latestRun.final_status} />}
            </div>
            <a
              href={`https://github.com/${fullName}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-zinc-400 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-white mt-0.5"
            >
              <ExternalLink size={11} />
              github.com/{fullName}
            </a>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={load}
            className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={() => setShowRunModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium hover:bg-zinc-700 dark:hover:bg-zinc-100 transition-colors"
          >
            <Play size={14} />
            Run Agent
          </button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Analytics summary cards */}
      {analytics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {
              icon: BarChart3,
              label: "Total Runs",
              value: analytics.summary?.total_runs ?? 0,
              accent: "default",
            },
            {
              icon: CheckCircle2,
              label: "Pass Rate",
              value: `${analytics.summary?.pass_rate ?? 0}%`,
              accent: "green",
            },
            {
              icon: Zap,
              label: "Avg Score",
              value:
                analytics.summary?.avg_score != null
                  ? `${analytics.summary.avg_score} pts`
                  : "—",
              accent: "amber",
            },
            {
              icon: Clock,
              label: "Avg Duration",
              value: fmt(analytics.summary?.avg_time_seconds),
              accent: "violet",
            },
          ].map(({ icon: Icon, label, value, accent }) => (
            <div
              key={label}
              className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4"
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${
                  accent === "green"
                    ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    : accent === "amber"
                      ? "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400"
                      : accent === "violet"
                        ? "bg-violet-50 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400"
                        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                }`}
              >
                <Icon size={16} />
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-500 mb-1">
                {label}
              </p>
              <p className="text-lg font-bold text-zinc-900 dark:text-white">
                {value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Bug distribution */}
      {analytics?.bug_type_distribution &&
        Object.keys(analytics.bug_type_distribution).length > 0 && (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-4">
              Bug Type Distribution
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {Object.entries(analytics.bug_type_distribution)
                .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
                .map(([type, count]) => (
                  <div
                    key={type}
                    className="flex items-center justify-between bg-zinc-50 dark:bg-zinc-800/40 rounded-lg px-3 py-2"
                  >
                    <span className="text-xs text-zinc-500 dark:text-zinc-400 font-mono">
                      {type}
                    </span>
                    <span className="text-sm font-bold text-zinc-900 dark:text-white">
                      {count}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

      {/* Run history table */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
            Run History
          </h2>
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            {runs.length} runs
          </span>
        </div>

        {loading ? (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-5 py-3.5 flex gap-3 items-center">
                <div className="h-4 w-4 rounded-full shimmer shrink-0" />
                <div className="h-4 w-40 shimmer rounded" />
                <div className="h-4 w-20 shimmer rounded ml-auto" />
              </div>
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <GitBranch
              size={32}
              className="text-zinc-300 dark:text-zinc-700 mx-auto mb-3"
            />
            <p className="text-sm text-zinc-400 dark:text-zinc-600">
              No runs yet for this repository.
            </p>
            <button
              onClick={() => setShowRunModal(true)}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium hover:bg-zinc-700 dark:hover:bg-zinc-100 transition-colors"
            >
              <Play size={13} /> Start First Run
            </button>
          </div>
        ) : (
          <>
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {runs.map((run) => (
                <Link
                  key={run.run_id}
                  href={`/run/${run.run_id}`}
                  className="flex items-center gap-3 px-5 py-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors group"
                >
                  {/* Status icon */}
                  <span className="shrink-0">
                    {run.final_status === "PASSED" ? (
                      <CheckCircle2 size={15} className="text-emerald-500" />
                    ) : run.final_status === "FAILED" ? (
                      <XCircle size={15} className="text-red-500" />
                    ) : (
                      <RefreshCw
                        size={15}
                        className="text-zinc-400 animate-spin"
                      />
                    )}
                  </span>

                  {/* Run ID + date */}
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-mono text-zinc-500 dark:text-zinc-400 truncate">
                      {run.run_id.slice(0, 8)}…
                    </p>
                    <p className="text-xs text-zinc-400 dark:text-zinc-600">
                      {run.started_at
                        ? new Date(run.started_at).toLocaleString()
                        : "—"}
                    </p>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-4 shrink-0 text-xs text-zinc-400 dark:text-zinc-500">
                    <span className="hidden sm:block">
                      {run.total_fixes_applied} fix
                      {run.total_fixes_applied !== 1 ? "es" : ""}
                    </span>
                    <span className="hidden sm:block font-mono text-zinc-500 dark:text-zinc-400">
                      {run.final_score ?? "—"} pts
                    </span>
                    <span className="hidden md:block">
                      {fmt(run.total_time_seconds)}
                    </span>
                    <RunStatusBadge status={run.final_status} />
                  </div>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            <div className="px-5 py-3.5 border-t border-zinc-100 dark:border-zinc-800/60 flex items-center justify-between">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="text-xs text-zinc-400 hover:text-zinc-900 dark:hover:text-white disabled:opacity-30 transition-colors"
              >
                ← Previous
              </button>
              <span className="text-xs text-zinc-400 dark:text-zinc-600">
                Page {page}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={runs.length < PAGE_SIZE}
                className="text-xs text-zinc-400 hover:text-zinc-900 dark:hover:text-white disabled:opacity-30 transition-colors"
              >
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
