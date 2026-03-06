// frontend/src/components/run/RunModal.tsx

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { X, Play, Loader2, GitBranch, Info } from "lucide-react";

import { startRun } from "@/lib/api";
import type { Repo } from "@/types/agent";

interface RunModalProps {
  repo: Repo;
  onClose: () => void;
}

export default function RunModal({ repo, onClose }: RunModalProps) {
  const router = useRouter();

  const [branchPrefix, setBranchPrefix] = useState("");
  const [maxIter, setMaxIter] = useState(5);
  const [readonly, setReadonly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const previewBranch = branchPrefix.trim()
    ? `${branchPrefix
        .trim()
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "_")}_AI_FIX_N`
    : "CI_HEALER_AI_FIX_N";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await startRun({
        repo_url: repo.html_url,
        branch_prefix: branchPrefix.trim(),
        max_iterations: maxIter,
        read_only: readonly,
      });
      router.push(`/run/${res.run_id}`);
    } catch (e) {
      setError((e as Error).message);
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
              Configure Run
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-500 mt-0.5 font-mono">
              {repo.full_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">
          {error && (
            <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3">
              {error}
            </div>
          )}

          {/* Branch prefix */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Branch Prefix{" "}
              <span className="text-zinc-400 dark:text-zinc-600 font-normal">
                (optional)
              </span>
            </label>
            <input
              type="text"
              value={branchPrefix}
              onChange={(e) => setBranchPrefix(e.target.value)}
              placeholder="e.g. MyTeam"
              maxLength={50}
              className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 dark:focus:ring-violet-400/50 transition-shadow"
            />
            <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 dark:text-zinc-500">
              <GitBranch size={10} />
              <span className="font-mono">{previewBranch}</span>
            </div>
          </div>

          {/* Max iterations */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Max Iterations
              <span className="ml-1.5 text-zinc-400 dark:text-zinc-600 font-normal">
                (1–10)
              </span>
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={10}
                value={maxIter}
                onChange={(e) => setMaxIter(Number(e.target.value))}
                className="flex-1 accent-violet-500"
              />
              <span className="text-sm font-semibold text-zinc-900 dark:text-white w-4 text-right tabular-nums">
                {maxIter}
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
              The agent will retry fixing CI failures up to {maxIter} time
              {maxIter !== 1 ? "s" : ""}.
            </p>
          </div>

          {/* Read-only */}
          <label className="flex items-start gap-2.5 cursor-pointer select-none p-3 rounded-lg border border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
            <input
              type="checkbox"
              checked={readonly}
              onChange={(e) => setReadonly(e.target.checked)}
              className="mt-0.5 w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 accent-violet-500"
            />
            <div>
              <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                Read-only mode
              </span>
              <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-0.5">
                Analyse and generate fixes but skip commits and PR creation.
              </p>
            </div>
          </label>

          {/* Info note */}
          <div className="flex items-start gap-2 text-[11px] text-zinc-400 dark:text-zinc-500 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg px-3 py-2.5">
            <Info size={11} className="shrink-0 mt-0.5" />
            <span>
              The agent will clone the repo, run static analysis &amp; tests,
              generate targeted fixes, and open a pull request automatically.
            </span>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-zinc-900 dark:bg-white hover:bg-zinc-700 dark:hover:bg-zinc-100 disabled:opacity-50 disabled:cursor-not-allowed text-white dark:text-zinc-900 text-sm font-semibold rounded-lg py-2.5 transition-colors"
          >
            {loading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Play size={14} />
            )}
            {loading ? "Starting…" : "Start Healing Run"}
          </button>
        </form>
      </div>
    </div>
  );
}
