// frontend/src/components/run/FixesTable.tsx

import type { Fix } from "@/types/agent";

const STATUS_STYLE: Record<string, string> = {
  FIXED:
    "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
  FAILED:
    "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/20",
  SKIPPED:
    "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700",
};

const BUG_STYLE: Record<string, string> = {
  LINTING:
    "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-700",
  SYNTAX:
    "bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-400 border-violet-200 dark:border-violet-500/20",
  LOGIC:
    "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/20",
  TYPEERROR:
    "bg-orange-50 dark:bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-500/20",
  IMPORT:
    "bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-500/20",
  INDENTATION:
    "bg-teal-50 dark:bg-teal-500/10 text-teal-700 dark:text-teal-400 border-teal-200 dark:border-teal-500/20",
};

export default function FixesTable({ fixes }: { fixes: Fix[] }) {
  if (!fixes.length) return null;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-white">
          Fixes Applied
          <span className="ml-2 text-xs text-zinc-400 dark:text-zinc-500 font-normal">
            {fixes.length} total
          </span>
        </h3>
      </div>
      <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
        {fixes.map((f, i) => (
          <div key={i} className="px-5 py-3 flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-mono text-zinc-700 dark:text-zinc-300 truncate">
                {f.file}
                {f.line_number ? (
                  <span className="text-zinc-400 dark:text-zinc-600">
                    :{f.line_number}
                  </span>
                ) : null}
              </p>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5 truncate">
                {f.commit_message}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${BUG_STYLE[f.bug_type] ?? ""}`}
              >
                {f.bug_type}
              </span>
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${STATUS_STYLE[f.status] ?? ""}`}
              >
                {f.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
