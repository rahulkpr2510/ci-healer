// frontend/src/components/run/AgentPipeline.tsx

"use client";

import {
  CheckCircle2,
  XCircle,
  Search,
  Code2,
  TestTube2,
  Brain,
  Wrench,
  GitCommit,
  GitPullRequest,
  Flag,
  Loader2,
  ScanSearch,
  FileCode2,
  AlertTriangle,
} from "lucide-react";
import type { RunStatus } from "@/types/agent";

interface PipelineStep {
  key: string;
  label: string;
  icon: React.ElementType;
  description: string;
  phase: "analysis" | "fix";
}

const STEPS: PipelineStep[] = [
  {
    key: "repo_analyzer",
    label: "Clone",
    icon: Search,
    description: "Clone & scan repository",
    phase: "analysis",
  },
  {
    key: "detect_lang",
    label: "Detect",
    icon: Code2,
    description: "Identify language stack",
    phase: "analysis",
  },
  {
    key: "static_analyzer",
    label: "Analyse",
    icon: Brain,
    description: "Run linters & type checkers",
    phase: "analysis",
  },
  {
    key: "run_tests",
    label: "Tests",
    icon: TestTube2,
    description: "Execute test suite",
    phase: "analysis",
  },
  {
    key: "failure_classifier",
    label: "Classify",
    icon: AlertTriangle,
    description: "Categorise failures",
    phase: "analysis",
  },
  {
    key: "fix_generator",
    label: "Fix",
    icon: ScanSearch,
    description: "AI generates patches",
    phase: "fix",
  },
  {
    key: "patch_applier",
    label: "Apply",
    icon: Wrench,
    description: "Write fixes to disk",
    phase: "fix",
  },
  {
    key: "git_commit",
    label: "Commit",
    icon: GitCommit,
    description: "Commit changes",
    phase: "fix",
  },
  {
    key: "create_pr",
    label: "PR",
    icon: GitPullRequest,
    description: "Open pull request",
    phase: "fix",
  },
  {
    key: "ci_monitor",
    label: "CI",
    icon: FileCode2,
    description: "Monitor CI pipeline",
    phase: "fix",
  },
  {
    key: "finalize",
    label: "Done",
    icon: Flag,
    description: "Compile results",
    phase: "fix",
  },
];

type StepStatus = "pending" | "running" | "done" | "error" | "skipped";

interface AgentPipelineProps {
  runStatus: RunStatus;
  logLines?: Array<{ type: string; node?: string; level?: string }>;
}

function inferStepStatuses(
  runStatus: RunStatus,
  logLines: Array<{ type: string; node?: string; level?: string }>,
): Record<string, StepStatus> {
  const runDone =
    runStatus === "PASSED" ||
    runStatus === "FAILED" ||
    runStatus === "NO_ISSUES";

  const startedNodes = new Set<string>();
  const endedNodes = new Set<string>();
  const errorNodes = new Set<string>();
  let lastStarted: string | null = null;

  for (const line of logLines) {
    if (!line.node) continue;
    if (line.type === "node_start") {
      startedNodes.add(line.node);
      lastStarted = line.node;
    } else if (line.type === "node_end") {
      endedNodes.add(line.node);
      if (line.level === "error") errorNodes.add(line.node);
    }
  }

  const activeNode =
    lastStarted && !endedNodes.has(lastStarted) ? lastStarted : null;
  const statuses: Record<string, StepStatus> = {};
  let passedActive = false;

  for (const step of STEPS) {
    const k = step.key;
    if (runDone) {
      if (startedNodes.has(k) || endedNodes.has(k)) {
        statuses[k] = errorNodes.has(k) ? "error" : "done";
      } else {
        statuses[k] = "skipped";
      }
    } else {
      if (k === activeNode) {
        statuses[k] = "running";
        passedActive = true;
      } else if (!passedActive && endedNodes.has(k)) {
        statuses[k] = errorNodes.has(k) ? "error" : "done";
      } else {
        statuses[k] = "pending";
      }
    }
  }

  return statuses;
}

// ── Style maps ──────────────────────────────────────────────

const NODE_CLS: Record<StepStatus, string> = {
  done: "border-emerald-500/70 bg-emerald-500/10 text-emerald-400 shadow-emerald-500/10",
  running:
    "border-violet-500 bg-violet-500/15 text-violet-300 ring-2 ring-violet-500/40 shadow-violet-500/20",
  error: "border-red-500/70 bg-red-500/10 text-red-400",
  pending: "border-zinc-700/60 bg-zinc-800/30 text-zinc-600",
  skipped: "border-zinc-800/40 bg-zinc-900/20 text-zinc-700 opacity-30",
};

const LABEL_CLS: Record<StepStatus, string> = {
  done: "text-zinc-300",
  running: "text-violet-400 font-semibold",
  error: "text-red-400",
  pending: "text-zinc-600",
  skipped: "text-zinc-700",
};

const CONNECTOR_BG: Record<StepStatus, string> = {
  done: "bg-emerald-500/50",
  running: "bg-violet-500/60",
  error: "bg-red-500/40",
  pending: "bg-zinc-800",
  skipped: "bg-zinc-800/30",
};

function StepNode({
  step,
  status,
}: {
  step: PipelineStep;
  status: StepStatus;
}) {
  const Icon = step.icon;
  const isDone = status === "done";
  const isError = status === "error";
  const isRun = status === "running";
  return (
    <div
      className="flex flex-col items-center gap-1.5 shrink-0"
      title={step.description}
    >
      <div
        className={`relative w-11 h-11 rounded-xl border-2 flex items-center justify-center transition-all duration-500 shadow ${NODE_CLS[status]}`}
      >
        {isRun ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <Icon size={16} />
        )}
        {isDone && (
          <CheckCircle2
            size={11}
            className="absolute -top-1.5 -right-1.5 text-emerald-400 bg-zinc-950 rounded-full"
          />
        )}
        {isError && (
          <XCircle
            size={11}
            className="absolute -top-1.5 -right-1.5 text-red-400 bg-zinc-950 rounded-full"
          />
        )}
      </div>
      <span
        className={`text-[10px] font-medium text-center leading-none transition-colors duration-300 w-12 truncate ${LABEL_CLS[status]}`}
      >
        {step.label}
      </span>
    </div>
  );
}

function Connector({ fromStatus }: { fromStatus: StepStatus }) {
  return (
    <div className="flex-1 flex items-center pb-[18px] min-w-[8px]">
      <div
        className={`h-px w-full transition-all duration-500 ${CONNECTOR_BG[fromStatus]}`}
      />
    </div>
  );
}

export default function AgentPipeline({
  runStatus,
  logLines = [],
}: AgentPipelineProps) {
  const statuses = inferStepStatuses(runStatus, logLines);
  const activeStep = STEPS.find((s) => statuses[s.key] === "running");
  const doneCount = STEPS.filter((s) => statuses[s.key] === "done").length;
  const totalCount = STEPS.length;

  // Phase labels split
  const analysisSteps = STEPS.filter((s) => s.phase === "analysis");
  const fixSteps = STEPS.filter((s) => s.phase === "fix");

  const runDone =
    runStatus === "PASSED" ||
    runStatus === "FAILED" ||
    runStatus === "NO_ISSUES";

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Agent Pipeline
          </h3>
          {activeStep && !runDone && (
            <span className="text-xs text-violet-400 bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 rounded-full animate-pulse">
              {activeStep.label}…
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className="text-zinc-300 font-medium tabular-nums">
              {doneCount}
            </span>
            <span>/ {totalCount} steps</span>
          </div>
          {runDone && (
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                runStatus === "PASSED"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : runStatus === "NO_ISSUES"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : "bg-red-500/10 text-red-400 border border-red-500/20"
              }`}
            >
              {runStatus}
            </span>
          )}
        </div>
      </div>

      {/* Single straight pipeline line */}
      {/* pt-3: gives room above for position:absolute badges (-top-1.5) that would
           otherwise be clipped by overflow-x-auto's implicit overflow-y boundary */}
      <div className="overflow-x-auto pt-3">
        <div className="flex items-end gap-0 w-full">
          {STEPS.map((step, i) => (
            <div key={step.key} className="contents">
              <StepNode step={step} status={statuses[step.key] ?? "pending"} />
              {i < STEPS.length - 1 && (
                <Connector fromStatus={statuses[step.key] ?? "pending"} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Phase labels */}
      <div className="mt-4 flex items-center gap-1 text-[10px] text-zinc-600 font-medium">
        <div
          style={{ width: `${(analysisSteps.length / totalCount) * 100}%` }}
          className="flex items-center gap-1.5 border-t border-zinc-800 pt-1.5"
        >
          <div className="w-1 h-1 rounded-full bg-zinc-600" />
          Analysis Phase
        </div>
        <div
          style={{ width: `${(fixSteps.length / totalCount) * 100}%` }}
          className="flex items-center gap-1.5 border-t border-zinc-800 pt-1.5 text-violet-600"
        >
          <div className="w-1 h-1 rounded-full bg-violet-600" />
          Fix &amp; Deploy Phase
        </div>
      </div>
    </div>
  );
}
