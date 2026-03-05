// frontend/src/app/run/[runId]/page.tsx

"use client";

import { useEffect, useCallback, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  GitBranch,
  Clock,
  Zap,
  ExternalLink,
  RefreshCw,
  Hash,
  Layers,
  AlertTriangle,
} from "lucide-react";

import { getRun, streamRun } from "@/lib/api";
import { useAgentStore } from "@/store/agentStore";
import type { SSEEvent } from "@/types/agent";

import RunStatusBadge from "@/components/ui/RunStatusBadge";
import LanguageBadge from "@/components/ui/LanguageBadge";
import LogStream from "@/components/run/LogStream";
import FixesTable from "@/components/run/FixesTable";
import AgentPipeline from "@/components/run/AgentPipeline";
import AgentErrorsPanel from "@/components/run/AgentErrorsPanel";

export default function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();

  const {
    activeRun,
    runLoading,
    runError,
    logLines,
    setActiveRunId,
    setActiveRun,
    setRunLoading,
    setRunError,
    appendLog,
    clearLogs,
    resetRun,
  } = useAgentStore();

  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const running = activeRun?.final_status === "RUNNING" || runLoading;

  // Live elapsed timer — counts up from started_at while run is RUNNING
  const [elapsedSecs, setElapsedSecs] = useState<number | null>(null);

  useEffect(() => {
    if (!activeRun || activeRun.final_status !== "RUNNING") {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setElapsedSecs(null);
      return;
    }
    const startMs = activeRun.timing?.started_at
      ? new Date(activeRun.timing.started_at).getTime()
      : Date.now();
    const tick = () => setElapsedSecs((Date.now() - startMs) / 1000);
    tick();
    timerRef.current = setInterval(tick, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [activeRun?.final_status, activeRun?.timing?.started_at]);

  // Stop any active polling interval
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const boot = useCallback(async () => {
    if (!runId) return;

    resetRun();
    clearLogs();
    setRunLoading(true);
    setRunError(null);
    setActiveRunId(runId);

    try {
      const run = await getRun(runId);
      setActiveRun(run);

      if (run.final_status === "RUNNING") {
        // SSE for live events
        esRef.current = streamRun(
          runId,
          (e: SSEEvent) => {
            appendLog(e);
            if (e.type === "complete" || e.type === "error") {
              stopPolling();
              getRun(runId)
                .then((updated) => {
                  setActiveRun(updated);
                })
                .catch(() => null);
            }
          },
          () => {
            // SSE closed — do a final DB refresh
            getRun(runId)
              .then(setActiveRun)
              .catch(() => null);
          },
        );

        // Polling fallback: every 5 s refresh run status from DB.
        // Ensures status never stays stuck as RUNNING if SSE drops.
        stopPolling();
        pollRef.current = setInterval(async () => {
          try {
            const updated = await getRun(runId);
            setActiveRun(updated);
            if (updated.final_status !== "RUNNING") {
              stopPolling();
            }
          } catch {
            // ignore transient errors
          }
        }, 5000);
      } else {
        // run already finished — build logs from stored data
        const syntheticLogs: SSEEvent[] = [];

        run.ci_timeline?.forEach((ev) => {
          syntheticLogs.push({
            type: "log",
            level:
              ev.status === "PASSED"
                ? "success"
                : ev.status === "FAILED"
                  ? "error"
                  : "info",
            text: `[Iteration ${ev.iteration}] ${ev.iteration_label} → ${ev.status}`,
          });
        });

        run.fixes?.forEach((f) => {
          syntheticLogs.push({
            type: "log",
            level:
              f.status === "FIXED"
                ? "success"
                : f.status === "FAILED"
                  ? "error"
                  : "warning",
            text: `${f.status}  ${f.bug_type}  ${f.file}${f.line_number ? `:${f.line_number}` : ""}  — ${f.commit_message}`,
          });
        });

        syntheticLogs.push({
          type: "complete",
          level: run.final_status === "PASSED" ? "success" : "error",
          text: `Run ${run.final_status} — score: ${run.score?.final_score ?? 0} pts, fixes: ${run.total_fixes_applied}`,
        });

        syntheticLogs.forEach(appendLog);
      }
    } catch (e) {
      setRunError((e as Error).message);
    } finally {
      setRunLoading(false);
    }
  }, [
    runId,
    resetRun,
    clearLogs,
    setRunLoading,
    setRunError,
    setActiveRunId,
    setActiveRun,
    appendLog,
    stopPolling,
  ]);

  useEffect(() => {
    boot();
    return () => {
      esRef.current?.close();
      stopPolling();
    };
  }, [boot, stopPolling]);

  function fmt(secs: number | null, live = false) {
    if (secs == null) return "—";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const base =
      m > 0
        ? `${m}m ${s.toString().padStart(2, "0")}s`
        : `${secs.toFixed(live ? 0 : 1)}s`;
    return live ? `⏱ ${base}` : base;
  }

  if (runLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-zinc-400">
        <RefreshCw size={14} className="animate-spin mr-2" /> Loading run…
      </div>
    );
  }

  if (runError) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
        >
          <ArrowLeft size={14} /> Back
        </button>
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-4">
          {runError}
        </div>
      </div>
    );
  }

  if (!activeRun) return null;

  const r = activeRun;

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Back */}
      <button
        onClick={() => router.push("/dashboard")}
        className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
      >
        <ArrowLeft size={14} /> Dashboard
      </button>

      {/* Run header card */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-base font-bold text-zinc-900 dark:text-white font-mono">
                {r.repo_owner}/{r.repo_name}
              </h1>
              <RunStatusBadge status={r.final_status} />
            </div>
            <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-1 font-mono truncate">
              run/{r.run_id}
            </p>
            {/* Language badge */}
            {r.primary_language && r.primary_language !== "Unknown" && (
              <div className="mt-2">
                <LanguageBadge language={r.primary_language} />
              </div>
            )}
          </div>

          {r.pr_url && (
            <a
              href={r.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 text-xs font-medium hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors shrink-0"
            >
              <ExternalLink size={11} /> View PR
            </a>
          )}
        </div>

        {/* Meta grid */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              icon: GitBranch,
              label: "Branch",
              value: r.branch_name ?? "—",
            },
            {
              icon: Clock,
              label: "Duration",
              value:
                elapsedSecs !== null
                  ? fmt(elapsedSecs, true)
                  : fmt(r.timing?.total_time_seconds ?? null),
            },
            {
              icon: Zap,
              label: "Score",
              value:
                r.score?.final_score != null
                  ? `${r.score.final_score} pts`
                  : "—",
            },
            {
              icon: RefreshCw,
              label: "Iterations / Commits",
              value: `${r.iterations_used ?? r.iterations_run ?? "—"} / ${r.total_commits ?? "—"}`,
            },
            {
              icon: Hash,
              label: "Failures Found",
              value: r.total_failures_detected ?? "—",
            },
            {
              icon: Layers,
              label: "Fixes Applied",
              value: r.total_fixes_applied ?? "—",
            },
          ].map(({ icon: Icon, label, value }) => (
            <div
              key={label}
              className="bg-zinc-50 dark:bg-zinc-800/40 rounded-lg px-3 py-2.5"
            >
              <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-500">
                <Icon size={11} />
                {label}
              </div>
              <p className="text-sm font-medium text-zinc-900 dark:text-white mt-1 truncate">
                {String(value)}
              </p>
            </div>
          ))}
        </div>

        {/* Team row */}
        <div className="mt-3 flex items-center gap-4 text-xs text-zinc-400 dark:text-zinc-600 flex-wrap">
          <span>
            Team:{" "}
            <span className="text-zinc-600 dark:text-zinc-400">
              {r.team_name}
            </span>
          </span>
          <span>
            Leader:{" "}
            <span className="text-zinc-600 dark:text-zinc-400">
              {r.team_leader}
            </span>
          </span>
          <span>
            Mode:{" "}
            <span className="text-zinc-600 dark:text-zinc-400">{r.mode}</span>
          </span>
          {r.detected_languages && r.detected_languages.length > 0 && (
            <span className="flex items-center gap-1.5 flex-wrap">
              <span className="text-zinc-400 dark:text-zinc-600">
                Languages:
              </span>
              {r.detected_languages.slice(0, 5).map((lang) => (
                <LanguageBadge key={lang} language={lang} size="sm" />
              ))}
            </span>
          )}
        </div>
      </div>

      {/* Agent pipeline visualization */}
      <AgentPipeline runStatus={r.final_status} logLines={logLines} />

      {/* Live log stream */}
      <LogStream lines={logLines} running={running} />

      {/* Fixes table */}
      {r.fixes?.length > 0 && <FixesTable fixes={r.fixes} />}

      {/* CI Timeline */}
      {r.ci_timeline?.length > 0 && (
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-white">
              CI Timeline
            </h3>
          </div>
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {r.ci_timeline.map((ev, i) => (
              <div key={i} className="px-5 py-3 flex items-center gap-3">
                <span className="text-xs text-zinc-400 dark:text-zinc-600 font-mono w-6">
                  {ev.iteration}
                </span>
                <RunStatusBadge status={ev.status} />
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  {ev.iteration_label}
                </span>
                {ev.ran_at && (
                  <span className="ml-auto text-xs text-zinc-400 dark:text-zinc-600">
                    {new Date(ev.ran_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Score breakdown */}
      {r.score && (
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-4">
            Score Breakdown
          </h3>

          {/* Score Progress Bar */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-zinc-500 dark:text-zinc-500">
                Final Score
              </span>
              <span className="text-2xl font-bold text-zinc-900 dark:text-white">
                {r.score.final_score}
                <span className="text-sm text-zinc-400 dark:text-zinc-500 font-normal ml-1">
                  / 110
                </span>
              </span>
            </div>
            <div className="h-3 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ease-out ${
                  r.score.final_score >= 100
                    ? "bg-emerald-500"
                    : r.score.final_score >= 70
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{
                  width: `${Math.min(100, (r.score.final_score / 110) * 100)}%`,
                }}
              />
            </div>
            <div className="flex justify-between mt-1 text-xs text-zinc-400 dark:text-zinc-600">
              <span>0</span>
              <span>50</span>
              <span>100</span>
              <span>110</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Base Score", value: r.score.base_score },
              { label: "Speed Bonus", value: `+${r.score.speed_bonus}` },
              {
                label: "Efficiency Penalty",
                value: `-${r.score.efficiency_penalty}`,
              },
              { label: "Final Score", value: r.score.final_score },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="bg-zinc-50 dark:bg-zinc-800/40 rounded-lg px-3 py-2.5"
              >
                <p className="text-xs text-zinc-500 dark:text-zinc-500">
                  {label}
                </p>
                <p className="text-lg font-bold text-zinc-900 dark:text-white mt-0.5">
                  {value}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent tool errors / warnings */}
      {r.agent_errors && r.agent_errors.length > 0 && (
        <AgentErrorsPanel errors={r.agent_errors} />
      )}
    </div>
  );
}
