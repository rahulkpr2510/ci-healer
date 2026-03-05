// frontend/src/components/run/LogStream.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  AlertTriangle,
  Wrench,
  TestTube2,
  PlayCircle,
  RefreshCw,
  Trophy,
  Terminal,
  Search,
  Code2,
  Brain,
  GitCommit,
  GitPullRequest,
  Flag,
  Copy,
  Check,
} from "lucide-react";
import type { SSEEvent } from "@/types/agent";

/* ─── Level colours ─────────────────────────── */
const LEVEL_STYLE: Record<string, string> = {
  info: "text-zinc-400",
  success: "text-emerald-400",
  warning: "text-amber-400",
  error: "text-red-400",
};

/* ─── Semantic event config ─────────────────── */
const EVENT_CONFIG: Record<
  string,
  { icon: React.ElementType; color: string; bgColor: string; label: string }
> = {
  AGENT_STARTED: {
    icon: PlayCircle,
    color: "text-zinc-300",
    bgColor: "bg-zinc-800/60",
    label: "AGENT_STARTED",
  },
  REPO_CLONED: {
    icon: CheckCircle2,
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    label: "REPO_CLONED",
  },
  TEST_DISCOVERED: {
    icon: TestTube2,
    color: "text-sky-400",
    bgColor: "bg-sky-500/10",
    label: "TEST_DISCOVERED",
  },
  TEST_FAILED: {
    icon: XCircle,
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    label: "TEST_FAILED",
  },
  FIX_GENERATED: {
    icon: Wrench,
    color: "text-violet-400",
    bgColor: "bg-violet-500/10",
    label: "FIX_GENERATED",
  },
  COMMIT_CREATED: {
    icon: GitCommit,
    color: "text-teal-400",
    bgColor: "bg-teal-500/10",
    label: "COMMIT_CREATED",
  },
  CI_RERUN: {
    icon: RefreshCw,
    color: "text-zinc-300",
    bgColor: "bg-zinc-800/40",
    label: "CI_RERUN",
  },
  RUN_COMPLETED: {
    icon: Trophy,
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    label: "RUN_COMPLETED",
  },
};

// Node-name → icon map for inline node labels
const NODE_ICONS: Record<string, React.ElementType> = {
  repo_analyzer: Search,
  detect_lang: Code2,
  static_analyzer: Brain,
  run_tests: TestTube2,
  failure_classifier: XCircle,
  fix_generator: Wrench,
  patch_applier: Code2,
  git_commit: GitCommit,
  ci_monitor: RefreshCw,
  create_pr: GitPullRequest,
  finalize: Flag,
};

/* ─── Format helper ─────────────────────────── */
function formatEvent(e: SSEEvent): {
  icon: React.ElementType | null;
  color: string;
  bgColor: string;
  label: string | null;
  text: string;
  isHighlight: boolean;
} {
  const config = EVENT_CONFIG[e.type];

  if (config) {
    let text = "";
    switch (e.type) {
      case "AGENT_STARTED":
        text = `Starting agent for ${e.repo_url ?? "repository"}`;
        break;
      case "REPO_CLONED":
        text = `Repository cloned  ·  branch: ${e.branch_name ?? "created"}`;
        if (e.primary_language) text += `  ·  ${e.primary_language}`;
        break;
      case "TEST_DISCOVERED":
        text = `Tests discovered${e.test_count ? ` — ${e.test_count} tests` : ""}`;
        break;
      case "TEST_FAILED":
        text = `${e.failures_count ?? 0} failure(s) detected`;
        break;
      case "FIX_GENERATED":
        text = `${e.file ?? "file"}${e.line ? `:${e.line}` : ""}  [${e.bug_type ?? "fix"}]  ${e.text ?? ""}`;
        break;
      case "COMMIT_CREATED":
        text = `${e.commit_count ?? 0} commit(s) created`;
        break;
      case "CI_RERUN":
        text = `Iteration ${e.iteration ?? "?"}  →  ${e.final_status ?? "checking"}`;
        break;
      case "RUN_COMPLETED": {
        const isNoIssues = e.final_status === "NO_ISSUES";
        text = isNoIssues
          ? (e.skip_reason ??
            `No issues found — repo is healthy  (${e.score ?? 0} pts)`)
          : `Run ${e.final_status ?? "finished"}  ·  Score: ${e.score ?? 0} pts`;
        break;
      }
      default:
        text = e.text ?? e.message ?? "";
    }
    return {
      icon: config.icon,
      color: config.color,
      bgColor: config.bgColor,
      label: config.label,
      text,
      isHighlight: true,
    };
  }

  if (e.type === "complete") {
    const isPass = e.final_status === "PASSED";
    const isNoIssues = e.final_status === "NO_ISSUES";
    const color = isPass
      ? "text-emerald-400"
      : isNoIssues
        ? "text-amber-400"
        : "text-red-400";
    return {
      icon: isPass || isNoIssues ? CheckCircle2 : XCircle,
      color,
      bgColor: isPass
        ? "bg-emerald-500/10"
        : isNoIssues
          ? "bg-amber-500/10"
          : "bg-red-500/10",
      label: "COMPLETE",
      text: isNoIssues
        ? "No issues found — repo is healthy"
        : `Run ${e.final_status ?? "completed"}`,
      isHighlight: true,
    };
  }

  if (e.type === "error") {
    return {
      icon: AlertCircle,
      color: "text-red-400",
      bgColor: "bg-red-500/10",
      label: "ERROR",
      text: e.message ?? "An error occurred",
      isHighlight: true,
    };
  }

  const isWarn =
    (e.text ?? e.message ?? "").startsWith("⚠") || e.level === "warning";
  if (isWarn) {
    return {
      icon: AlertTriangle,
      color: "text-amber-400",
      bgColor: "transparent",
      label: null,
      text: e.text ?? e.message ?? "",
      isHighlight: false,
    };
  }

  return {
    icon: null,
    color: LEVEL_STYLE[e.level ?? "info"] ?? "text-zinc-400",
    bgColor: "transparent",
    label: null,
    text: e.text ?? e.message ?? JSON.stringify(e),
    isHighlight: false,
  };
}

/* ─── Component ─────────────────────────────── */
interface LogStreamProps {
  lines: SSEEvent[];
  running: boolean;
}

export default function LogStream({ lines, running }: LogStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  function handleCopy() {
    const text = lines
      .filter((e) => e.type !== "ping")
      .map((e) => {
        const { label, text } = formatEvent(e);
        return label ? `[${label}] ${text}` : text;
      })
      .join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/80">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
        <div className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
        <span className="ml-2.5 text-xs text-zinc-600 font-mono flex items-center gap-1.5">
          <Terminal size={10} />
          agent output
        </span>
        <div className="ml-auto flex items-center gap-3">
          {running && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              live
            </span>
          )}
          {lines.length > 0 && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-300 transition-colors"
              title="Copy logs"
            >
              {copied ? (
                <Check size={11} className="text-emerald-400" />
              ) : (
                <Copy size={11} />
              )}
            </button>
          )}
          <span className="text-[10px] text-zinc-700 tabular-nums">
            {lines.filter((l) => l.type !== "ping").length} lines
          </span>
        </div>
      </div>

      {/* Log lines */}
      <div className="h-96 overflow-y-auto p-3 font-mono text-xs space-y-0.5">
        {lines.length === 0 ? (
          <div className="flex items-center gap-2 text-zinc-700 py-2">
            <span className="animate-pulse">▊</span>
            <span>Waiting for agent output…</span>
          </div>
        ) : (
          lines.map((e, i) => {
            if (e.type === "ping") return null;

            const {
              icon: Icon,
              color,
              bgColor,
              label,
              text,
              isHighlight,
            } = formatEvent(e);

            const nodeIcon = e.node ? NODE_ICONS[e.node] : null;
            const NodeIconEl = nodeIcon;

            if (isHighlight) {
              return (
                <div
                  key={i}
                  className={`flex items-start gap-2 leading-5 rounded-md px-2 py-1 my-0.5 ${bgColor}`}
                >
                  <span className="text-zinc-700 shrink-0 select-none w-7 text-[10px] pt-0.5">
                    {String(i + 1).padStart(3, "0")}
                  </span>
                  {Icon && (
                    <Icon size={13} className={`${color} shrink-0 mt-0.5`} />
                  )}
                  {label && (
                    <span
                      className={`${color} shrink-0 font-semibold text-[10px]`}
                    >
                      [{label}]
                    </span>
                  )}
                  <span className={`${color} leading-relaxed flex-1`}>
                    {text}
                  </span>
                </div>
              );
            }

            return (
              <div
                key={i}
                className="flex items-start gap-2 leading-5 px-2 py-0.5"
              >
                <span className="text-zinc-800 shrink-0 select-none w-7 text-[10px]">
                  {String(i + 1).padStart(3, "0")}
                </span>
                {NodeIconEl && (
                  <NodeIconEl
                    size={11}
                    className="text-zinc-600 shrink-0 mt-0.5"
                  />
                )}
                {Icon ? (
                  <Icon size={11} className={`${color} shrink-0 mt-0.5`} />
                ) : (
                  <span className="w-[11px] shrink-0" />
                )}
                <span className={`${color} leading-relaxed`}>{text}</span>
              </div>
            );
          })
        )}
        {running && (
          <div className="flex items-center gap-1 text-zinc-700 px-2 py-0.5">
            <span className="animate-pulse text-violet-500">▊</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
