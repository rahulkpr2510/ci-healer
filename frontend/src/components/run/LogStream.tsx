// frontend/src/components/run/LogStream.tsx

"use client";

import { useEffect, useRef } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  GitBranch,
  Wrench,
  TestTube2,
  PlayCircle,
  RefreshCw,
  Trophy,
} from "lucide-react";
import type { SSEEvent } from "@/types/agent";

const LEVEL_STYLE: Record<string, string> = {
  info: "text-zinc-300",
  success: "text-emerald-400",
  warning: "text-amber-400",
  error: "text-red-400",
};

// Map semantic event types to display config
const EVENT_CONFIG: Record<
  string,
  { icon: React.ElementType; color: string; label: string }
> = {
  AGENT_STARTED: {
    icon: PlayCircle,
    color: "text-zinc-300",
    label: "AGENT_STARTED",
  },
  REPO_CLONED: {
    icon: CheckCircle2,
    color: "text-emerald-400",
    label: "REPO_CLONED",
  },
  TEST_DISCOVERED: {
    icon: TestTube2,
    color: "text-zinc-300",
    label: "TEST_DISCOVERED",
  },
  TEST_FAILED: {
    icon: XCircle,
    color: "text-amber-400",
    label: "TEST_FAILED",
  },
  FIX_GENERATED: {
    icon: Wrench,
    color: "text-violet-400",
    label: "FIX_GENERATED",
  },
  COMMIT_CREATED: {
    icon: GitBranch,
    color: "text-teal-400",
    label: "COMMIT_CREATED",
  },
  CI_RERUN: { icon: RefreshCw, color: "text-zinc-300", label: "CI_RERUN" },
  RUN_COMPLETED: {
    icon: Trophy,
    color: "text-emerald-400",
    label: "RUN_COMPLETED",
  },
};

function formatEvent(e: SSEEvent): {
  icon: React.ElementType | null;
  color: string;
  text: string;
} {
  const config = EVENT_CONFIG[e.type];

  if (config) {
    let text = "";
    switch (e.type) {
      case "AGENT_STARTED":
        text = `Starting agent for ${e.repo_url ?? "repository"}`;
        break;
      case "REPO_CLONED":
        text = `Repository cloned, branch: ${e.branch_name ?? "created"}`;
        break;
      case "TEST_DISCOVERED":
        text = `Tests discovered`;
        break;
      case "TEST_FAILED":
        text = `${e.failures_count ?? 0} failure(s) detected`;
        break;
      case "FIX_GENERATED":
        text = `${e.file ?? "file"}${e.line ? `:${e.line}` : ""} ${e.bug_type ?? ""} - ${e.text ?? "fixed"}`;
        break;
      case "COMMIT_CREATED":
        text = `${e.commit_count ?? 0} commit(s) created`;
        break;
      case "CI_RERUN":
        text = `Iteration ${e.iteration ?? "?"}: ${e.final_status ?? "checking"}`;
        break;
      case "RUN_COMPLETED":
        text = `Run ${e.final_status ?? "finished"} - Score: ${e.score ?? 0} pts`;
        break;
      default:
        text = e.text ?? e.message ?? "";
    }
    return { icon: config.icon, color: config.color, text };
  }

  // Fallback for log/complete/error/ping events
  if (e.type === "complete") {
    return {
      icon: CheckCircle2,
      color: e.final_status === "PASSED" ? "text-emerald-400" : "text-red-400",
      text: `Run ${e.final_status ?? "completed"}`,
    };
  }

  if (e.type === "error") {
    return {
      icon: AlertCircle,
      color: "text-red-400",
      text: e.message ?? "An error occurred",
    };
  }

  return {
    icon: null,
    color: LEVEL_STYLE[e.level ?? "info"] ?? "text-zinc-300",
    text: e.text ?? e.message ?? JSON.stringify(e),
  };
}

interface LogStreamProps {
  lines: SSEEvent[];
  running: boolean;
}

export default function LogStream({ lines, running }: LogStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/60">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
        <span className="ml-2 text-xs text-zinc-600 font-mono">
          agent output
        </span>
        {running && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            live
          </span>
        )}
      </div>

      {/* Log lines */}
      <div className="h-96 overflow-y-auto p-4 font-mono text-xs space-y-1">
        {lines.length === 0 ? (
          <span className="text-zinc-700">Waiting for agent output...</span>
        ) : (
          lines.map((e, i) => {
            // Skip ping events
            if (e.type === "ping") return null;

            const { icon: Icon, color, text } = formatEvent(e);
            const config = EVENT_CONFIG[e.type];

            return (
              <div key={i} className="flex items-start gap-2 leading-5">
                <span className="text-zinc-700 shrink-0 select-none w-8">
                  {String(i + 1).padStart(3, "0")}
                </span>
                {Icon && (
                  <Icon size={14} className={`${color} shrink-0 mt-0.5`} />
                )}
                {config && (
                  <span className={`${config.color} shrink-0`}>
                    [{config.label}]
                  </span>
                )}
                <span className={color}>{text}</span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
