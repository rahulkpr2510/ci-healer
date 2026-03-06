// frontend/src/app/run/[runId]/page.tsx

"use client";

import { useEffect, useCallback, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  GitBranch,
  Clock,
  ExternalLink,
  RefreshCw,
  Hash,
  Layers,
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
  // Tracks whether the current useEffect invocation has been superseded (handles
  // React 18 Strict Mode double-invoke and genuine re-mounts).
  const cancelledRef = useRef(false);
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

  useEffect(() => {
    if (!runId) return;

    // Cancel the previous invocation (React 18 Strict Mode double-invoke guard).
    // We close the old SSE and mark anything still in-flight as stale so its
    // callbacks never touch state.
    cancelledRef.current = true;
    esRef.current?.close();
    esRef.current = null;
    stopPolling();

    // Arm a fresh cancellation token for this invocation.
    cancelledRef.current = false;

    resetRun();
    clearLogs();
    setRunLoading(true);
    setRunError(null);
    setActiveRunId(runId);

    (async () => {
      try {
        const run = await getRun(runId);
        if (cancelledRef.current) return;
        setActiveRun(run);

        if (run.final_status === "RUNNING") {
          // SSE for live events
          const startPollingFallback = () => {
            if (pollRef.current) return; // already polling
            pollRef.current = setInterval(async () => {
              if (cancelledRef.current) {
                stopPolling();
                return;
              }
              try {
                const updated = await getRun(runId);
                if (!cancelledRef.current) {
                  setActiveRun(updated);
                  if (updated.final_status !== "RUNNING") stopPolling();
                }
              } catch {
                // ignore transient errors
              }
            }, 30_000);
          };

          esRef.current = streamRun(
            runId,
            (e: SSEEvent) => {
              if (cancelledRef.current) return;
              appendLog(e);
              if (e.type === "complete" || e.type === "error") {
                stopPolling();
                getRun(runId)
                  .then((updated) => {
                    if (!cancelledRef.current) setActiveRun(updated);
                  })
                  .catch(() => null);
              }
            },
            () => {
              // SSE closed — do a final DB refresh
              if (cancelledRef.current) return;
              getRun(runId)
                .then((r) => {
                  if (!cancelledRef.current) setActiveRun(r);
                })
                .catch(() => null);
            },
            () => {
              // SSE error — fall back to polling so UI stays responsive
              if (!cancelledRef.current) startPollingFallback();
            },
          );
        } else {
          // run already finished — build logs from stored data
          const syntheticLogs: SSEEvent[] = [];

          // Preamble — start + language
          syntheticLogs.push({
            type: "AGENT_STARTED",
            repo_url: run.repo_url,
          });
          if (run.primary_language) {
            syntheticLogs.push({
              type: "log",
              level: "success",
              text: `  Language: ${run.primary_language}${run.detected_languages?.length ? `  (${run.detected_languages.join(", ")})` : ""}`,
            });
          }

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

          // Agent-level tool errors (e.g. linter not found)
          run.agent_errors?.forEach((err) => {
            syntheticLogs.push({
              type: "log",
              level: "warning",
              text: `⚠️  ${err}`,
            });
          });

          // Skip reason for NO_ISSUES runs
          if (run.final_status === "NO_ISSUES") {
            syntheticLogs.push({
              type: "log",
              level: "info",
              text: `ℹ️  ${run.skip_reason ?? "No issues to fix — repo is healthy"}`,
            });
          }

          syntheticLogs.push({
            type: "complete",
            final_status: run.final_status,
            skip_reason:
              run.final_status === "NO_ISSUES"
                ? "No issues found — repo is healthy"
                : undefined,
            level:
              run.final_status === "PASSED" || run.final_status === "NO_ISSUES"
                ? "success"
                : "error",
            text: `Run ${run.final_status}  ·  fixes: ${run.total_fixes_applied ?? 0}`,
          });

          if (!cancelledRef.current) syntheticLogs.forEach(appendLog);
        }
      } catch (e) {
        if (!cancelledRef.current) setRunError((e as Error).message);
      } finally {
        if (!cancelledRef.current) setRunLoading(false);
      }
    })();

    return () => {
      cancelledRef.current = true;
      esRef.current?.close();
      esRef.current = null;
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]); // Zustand actions are stable refs — only runId causes a true re-run

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
    <div className="space-y-5 max-w-full">
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

        {/* Language row */}
        {r.detected_languages && r.detected_languages.length > 0 && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-zinc-500 dark:text-zinc-600">
              Languages:
            </span>
            {r.detected_languages.slice(0, 5).map((lang) => (
              <LanguageBadge key={lang} language={lang} size="sm" />
            ))}
            {r.mode && (
              <span className="ml-2 text-xs text-zinc-500">
                Mode: <span className="text-zinc-400">{r.mode}</span>
              </span>
            )}
          </div>
        )}
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

      {/* Agent tool errors / warnings */}
      {r.agent_errors && r.agent_errors.length > 0 && (
        <AgentErrorsPanel errors={r.agent_errors} />
      )}
    </div>
  );
}
