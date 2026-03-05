// frontend/src/components/run/FixesTable.tsx

"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileCode2 } from "lucide-react";
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
  COMPILATION:
    "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/20",
  RUNTIME:
    "bg-pink-50 dark:bg-pink-500/10 text-pink-700 dark:text-pink-400 border-pink-200 dark:border-pink-500/20",
  DEPENDENCY:
    "bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/20",
  SECURITY:
    "bg-red-50 dark:bg-red-500/10 text-red-800 dark:text-red-300 border-red-300 dark:border-red-500/30",
  FORMATTING:
    "bg-zinc-50 dark:bg-zinc-800/80 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700",
};

interface FixWithDiff extends Fix {
  diff?: string;
}

function DiffBlock({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <div className="mt-2 rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700 font-mono text-[10px]">
      {lines.map((line, i) => {
        const isAdd = line.startsWith("+") && !line.startsWith("+++");
        const isDel = line.startsWith("-") && !line.startsWith("---");
        const isHunk = line.startsWith("@@");
        return (
          <div
            key={i}
            className={
              isAdd
                ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 px-3 py-0.5"
                : isDel
                  ? "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-300 px-3 py-0.5"
                  : isHunk
                    ? "bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 px-3 py-0.5"
                    : "text-zinc-500 dark:text-zinc-500 px-3 py-0.5"
            }
          >
            {line || " "}
          </div>
        );
      })}
    </div>
  );
}

function FixRow({ fix, index }: { fix: FixWithDiff; index: number }) {
  const [open, setOpen] = useState(false);
  const hasDiff = Boolean(fix.diff);

  return (
    <div className="border-b border-zinc-100 dark:border-zinc-800/60 last:border-0">
      <div
        className={`px-5 py-3 flex items-start gap-3 ${hasDiff ? "cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors" : ""}`}
        onClick={() => hasDiff && setOpen((v) => !v)}
      >
        {/* Index */}
        <span className="text-[10px] text-zinc-400 dark:text-zinc-600 font-mono w-5 shrink-0 pt-0.5">
          {String(index + 1).padStart(2, "0")}
        </span>

        {/* File + message */}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-mono text-zinc-700 dark:text-zinc-300 truncate flex items-center gap-1.5">
            <FileCode2
              size={11}
              className="text-zinc-400 dark:text-zinc-600 shrink-0"
            />
            {fix.file}
            {fix.line_number ? (
              <span className="text-zinc-400 dark:text-zinc-600">
                :{fix.line_number}
              </span>
            ) : null}
          </p>
          <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5 truncate">
            {fix.commit_message}
          </p>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2 shrink-0">
          <span
            className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${BUG_STYLE[fix.bug_type] ?? "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700"}`}
          >
            {fix.bug_type}
          </span>
          <span
            className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${STATUS_STYLE[fix.status] ?? ""}`}
          >
            {fix.status}
          </span>
          {hasDiff && (
            <span className="text-zinc-400 dark:text-zinc-600">
              {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </span>
          )}
        </div>
      </div>

      {/* Expandable diff */}
      {open && fix.diff && (
        <div className="px-5 pb-3">
          <DiffBlock diff={fix.diff} />
        </div>
      )}
    </div>
  );
}

export default function FixesTable({ fixes }: { fixes: FixWithDiff[] }) {
  if (!fixes.length) return null;

  const fixed = fixes.filter((f) => f.status === "FIXED").length;
  const failed = fixes.filter((f) => f.status === "FAILED").length;
  const skipped = fixes.filter((f) => f.status === "SKIPPED").length;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800 flex items-center gap-3 flex-wrap">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-white flex-1">
          Fixes Applied
        </h3>
        <div className="flex items-center gap-2 text-[11px] font-medium">
          <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {fixed} fixed
          </span>
          {failed > 0 && (
            <span className="text-red-600 dark:text-red-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
              {failed} failed
            </span>
          )}
          {skipped > 0 && (
            <span className="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
              {skipped} skipped
            </span>
          )}
          <span className="text-zinc-400 dark:text-zinc-600">
            · {fixes.length} total
          </span>
        </div>
      </div>
      <div>
        {fixes.map((f, i) => (
          <FixRow key={i} fix={f} index={i} />
        ))}
      </div>
    </div>
  );
}
