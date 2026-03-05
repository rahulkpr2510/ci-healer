// frontend/src/app/analytics/page.tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  Wrench,
  GitBranch,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

import { getDashboardSummary, getAllHistory } from "@/lib/api";
import type { DashboardSummary, RunSummary } from "@/types/agent";
import RunStatusBadge from "@/components/ui/RunStatusBadge";

const ACCENT_STYLES = {
  default:
    "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700",
  green:
    "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
  amber:
    "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/20",
};

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, h] = await Promise.all([
        getDashboardSummary(),
        getAllHistory(1, 30),
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

  // Chart data: last 20 runs by score (oldest first)
  const chartData = runs
    .slice(0, 20)
    .reverse()
    .map((r, i) => ({
      name: `#${i + 1}`,
      score: r.final_score ?? 0,
      status: r.final_status,
    }));

  const statCards: {
    label: string;
    value: string | number;
    icon: React.ElementType;
    accent: keyof typeof ACCENT_STYLES;
  }[] = [
    {
      label: "Total Runs",
      value: summary?.total_runs ?? "—",
      icon: GitBranch,
      accent: "default",
    },
    {
      label: "Pass Rate",
      value: summary ? `${summary.pass_rate ?? 0}%` : "—",
      icon: CheckCircle2,
      accent: "green",
    },
    {
      label: "Total Fixes",
      value: summary?.total_fixes_applied ?? "—",
      icon: Wrench,
      accent: "amber",
    },
    {
      label: "Unique Repos",
      value: summary?.unique_repos ?? "—",
      icon: GitBranch,
      accent: "default",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-white">
            Analytics
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Insights across all your CI healing runs.
          </p>
        </div>
        <button
          onClick={load}
          className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon: Icon, accent }) => (
          <div
            key={label}
            className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 flex items-start gap-4"
          >
            <div
              className={`w-9 h-9 rounded-lg border flex items-center justify-center shrink-0 ${ACCENT_STYLES[accent]}`}
            >
              {loading ? (
                <div className="w-4 h-4 shimmer rounded" />
              ) : (
                <Icon size={16} />
              )}
            </div>
            <div className="min-w-0">
              <p className="text-xs text-zinc-500 font-medium">{label}</p>
              {loading ? (
                <div className="h-7 w-14 shimmer rounded mt-1" />
              ) : (
                <p className="text-2xl font-bold text-zinc-900 dark:text-white mt-0.5">
                  {value}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Score trend chart */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-white mb-4">
          Score Trend
          <span className="ml-2 text-xs font-normal text-zinc-400 dark:text-zinc-500">
            last 20 runs
          </span>
        </h2>
        {loading ? (
          <div className="h-52 shimmer rounded-lg" />
        ) : chartData.length === 0 ? (
          <div className="h-52 flex items-center justify-center text-sm text-zinc-400 dark:text-zinc-600">
            No data yet.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} barCategoryGap={6}>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 110]}
                tick={{ fontSize: 11, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  background: "#18181b",
                  border: "1px solid #3f3f46",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "#fff",
                }}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                formatter={(val: unknown) => [`${val ?? 0} pts`, "Score"]}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={
                      entry.status === "PASSED"
                        ? "#10b981"
                        : entry.status === "FAILED"
                          ? "#ef4444"
                          : entry.status === "NO_ISSUES"
                            ? "#f59e0b"
                            : "#71717a"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* All runs list */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
            All Runs
          </h2>
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            {runs.length} loaded
          </span>
        </div>
        {loading ? (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-5 py-3.5 flex gap-3 items-center">
                <div className="h-3.5 w-3.5 shimmer rounded-full" />
                <div className="h-3.5 w-40 shimmer rounded" />
                <div className="h-3.5 w-16 shimmer rounded ml-auto" />
              </div>
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-zinc-400 dark:text-zinc-600">
            No runs yet.
          </div>
        ) : (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {runs.map((r) => (
              <a
                key={r.run_id}
                href={`/run/${r.run_id}`}
                className="flex items-center gap-3 px-5 py-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors"
              >
                {r.final_status === "PASSED" ? (
                  <CheckCircle2
                    size={14}
                    className="text-emerald-500 shrink-0"
                  />
                ) : r.final_status === "FAILED" ? (
                  <XCircle size={14} className="text-red-500 shrink-0" />
                ) : (
                  <RefreshCw
                    size={14}
                    className="text-zinc-400 animate-spin shrink-0"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-zinc-800 dark:text-zinc-200 font-medium truncate">
                    {r.repo_owner}/{r.repo_name}
                  </p>
                  {r.started_at && (
                    <p className="text-xs text-zinc-400 dark:text-zinc-600">
                      {new Date(r.started_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-400 dark:text-zinc-500">
                  <span className="hidden sm:block font-mono">
                    {r.final_score ?? "—"} pts
                  </span>
                  <RunStatusBadge status={r.final_status} />
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
