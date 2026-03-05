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
}

// Row 1: analysis phase (left → right)
const ROW1: PipelineStep[] = [
  { key: "repo_analyzer",      label: "Clone Repo",      icon: Search,         description: "Scanning repository structure" },
  { key: "detect_lang",        label: "Detect Lang",     icon: Code2,          description: "Identifying language stack" },
  { key: "static_analyzer",    label: "Static Analysis", icon: Brain,          description: "Running linters & type checkers" },
  { key: "run_tests",          label: "Run Tests",       icon: TestTube2,      description: "Executing test suite" },
  { key: "failure_classifier", label: "Classify",        icon: AlertTriangle,  description: "Categorising failing tests" },
  { key: "fix_generator",      label: "Generate Fix",    icon: ScanSearch,     description: "AI generating patch candidates" },
];

// Row 2: remediation phase (left → right)
const ROW2: PipelineStep[] = [
  { key: "patch_applier", label: "Apply Patch",  icon: Wrench,        description: "Writing fixes to files" },
  { key: "git_commit",    label: "Git Commit",   icon: GitCommit,     description: "Committing changes" },
  { key: "ci_monitor",    label: "CI Monitor",   icon: FileCode2,     description: "Monitoring CI pipeline" },
  { key: "create_pr",     label: "Create PR",    icon: GitPullRequest,description: "Opening pull request" },
  { key: "finalize",      label: "Finalize",     icon: Flag,          description: "Compiling results" },
];

const ALL_STEPS = [...ROW1, ...ROW2];

type StepStatus = "pending" | "running" | "done" | "error" | "skipped";

interface AgentPipelineProps {
  runStatus: RunStatus;
  logLines?: Array<{ type: string; node?: string; level?: string }>;
}

function inferStepStatuses(
  runStatus: RunStatus,
  logLines: Array<{ type: string; node?: string; level?: string }>,
): { statuses: Record<string, StepStatus>; activeNode: string | null } {
  const runDone =
    runStatus === "PASSED" || runStatus === "FAILED" || runStatus === "NO_ISSUES";

  const startedNodes = new Set<string>();
  const endedNodes   = new Set<string>();
  const errorNodes   = new Set<string>();
  let lastStartedNode: string | null = null;

  for (const line of logLines) {
    if (!line.node) continue;
    if (line.type === "node_start") {
      startedNodes.add(line.node);
      lastStartedNode = line.node;
    } else if (line.type === "node_end") {
      endedNodes.add(line.node);
      if (line.level === "error") errorNodes.add(line.node);
    }
  }

  const activeNode =
    lastStartedNode && !endedNodes.has(lastStartedNode) ? lastStartedNode : null;

  const statuses: Record<string, StepStatus> = {};
  let passedActive = false;

  for (const step of ALL_STEPS) {
    const k = step.key;
    if (runDone) {
      statuses[k] =
        startedNodes.has(k) || endedNodes.has(k)
          ? errorNodes.has(k) ? "error" : "done"
          : "skipped";
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

  return { statuses, activeNode };
}

// ── Style maps ──────────────────────────────────────────────

const NODE_CLS: Record<StepStatus, string> = {
  done:    "border-emerald-500/60 bg-emerald-500/10 text-emerald-400",
  running: "border-violet-500 bg-violet-500/15 text-violet-300 ring-2 ring-violet-500/40 ring-offset-2 ring-offset-zinc-950",
  error:   "border-red-500/60 bg-red-500/10 text-red-400",
  pending: "border-zinc-700 bg-zinc-800/40 text-zinc-600",
  skipped: "border-zinc-700/40 bg-zinc-800/20 text-zinc-700 opacity-40",
};

const LABEL_CLS: Record<StepStatus, string> = {
  done:    "text-zinc-300",
  running: "text-violet-400 font-semibold",
  error:   "text-red-400",
  pending: "text-zinc-600",
  skipped: "text-zinc-700",
};

const CONNECTOR_CLS = (s: StepStatus) =>
  s === "done"
    ? "bg-emerald-500/50"
    : s === "running"
      ? "bg-violet-500/60"
      : s === "error"
        ? "bg-red-500/30"
        : "bg-zinc-800";

// ── Sub-components ───────────────────────────────────────────

function StepNode({ step, status }: { step: PipelineStep; status: StepStatus }) {
  const Icon = step.icon;
  const isRunning = status === "running";
  const isDone    = status === "done";
  const isError   = status === "error";

  return (
    <div className="flex flex-col items-center gap-1.5 w-[72px]" title={step.description}>
      <div
        className={`relative w-10 h-10 rounded-xl border-2 flex items-center justify-center transition-all duration-500 ${NODE_CLS[status]} ${isRunning ? "glow-violet" : ""}`}
      >
        {isRunning ? (
          <Loader2 size={15} className="animate-spin text-violet-400" />
        ) : (
          <Icon size={15} />
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
        className={`text-[9px] font-medium text-center leading-tight transition-colors duration-300 ${LABEL_CLS[status]}`}
      >
        {step.label}
      </span>
    </div>
  );
}

function HConnector({ status }: { status: StepStatus }) {
  return (
    <div className="flex items-center pb-[18px] px-0.5">
      <div className={`h-px w-5 transition-colors duration-500 ${CONNECTOR_CLS(status)}`} />
    </div>
  );
}

// ── Main component ───────────────────────────────────────────

export default function AgentPipeline({
  runStatus,
  logLines = [],
}: AgentPipelineProps) {
  const { statuses, activeNode } = inferStepStatuses(runStatus, logLines);
  const activeLabel = activeNode ? ALL_STEPS.find((s) => s.key === activeNode)?.label : null;

  // Bridge status — colours the inter-row connector
  const bridgeStatus = statuses["fix_generator"] ?? "pending";
  const bridgeCls = CONNECTOR_CLS(bridgeStatus);

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Agent Pipeline
        </h3>
        {runStatus === "RUNNING" ? (
          <span className="flex items-center gap-1.5 text-xs text-violet-400">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            {activeLabel ? `Running: ${activeLabel}` : "Processing…"}
          </span>
        ) : runStatus === "PASSED" || runStatus === "NO_ISSUES" ? (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <CheckCircle2 size={11} /> Complete
          </span>
        ) : runStatus === "FAILED" ? (
          <span className="flex items-center gap-1.5 text-xs text-red-400">
            <XCircle size={11} /> Failed
          </span>
        ) : null}
      </div>

      {/* Two-row snake layout */}
      <div className="space-y-3">

        {/* ── Row 1: Analysis phase (left → right) ── */}
        <div className="flex items-center flex-wrap gap-y-2">
          {ROW1.map((step, i) => (
            <div key={step.key} className="flex items-center">
              <StepNode step={step} status={statuses[step.key] ?? "pending"} />
              {i < ROW1.length - 1 && (
                <HConnector status={statuses[step.key] ?? "pending"} />
              )}
            </div>
          ))}
        </div>

        {/* ── Bridge: full-width line with centred label ── */}
        <div className="flex items-center gap-2 px-1">
          <div className={`flex-1 h-px transition-colors duration-500 ${bridgeCls}`} />
          <span className={`text-[9px] font-medium uppercase tracking-wider transition-colors duration-300 ${
            bridgeStatus === "done" || bridgeStatus === "running"
              ? "text-zinc-500"
              : "text-zinc-700"
          }`}>
            Remediation
          </span>
          <div className={`flex-1 h-px transition-colors duration-500 ${bridgeCls}`} />
        </div>

        {/* ── Row 2: Remediation phase (left → right) ── */}
        <div className="flex items-center flex-wrap gap-y-2">
          {ROW2.map((step, i) => (
            <div key={step.key} className="flex items-center">
              <StepNode step={step} status={statuses[step.key] ?? "pending"} />
              {i < ROW2.length - 1 && (
                <HConnector status={statuses[step.key] ?? "pending"} />
              )}
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
