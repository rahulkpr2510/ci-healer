// frontend/src/components/ui/RunStatusBadge.tsx

import type { RunStatus } from "@/types/agent";

const STYLES: Record<RunStatus, string> = {
  RUNNING:
    "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-300 dark:border-zinc-700",
  PASSED:
    "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
  FAILED:
    "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/20",
  NO_ISSUES:
    "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/20",
};

const LABELS: Record<RunStatus, string> = {
  RUNNING: "RUNNING",
  PASSED: "PASSED",
  FAILED: "FAILED",
  NO_ISSUES: "NO ISSUES",
};

export default function RunStatusBadge({ status }: { status: RunStatus }) {
  const style = STYLES[status] ?? STYLES.FAILED;
  const label = LABELS[status] ?? status;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[11px] font-semibold ${style}`}
    >
      {label}
    </span>
  );
}
