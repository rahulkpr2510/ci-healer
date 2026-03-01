// frontend/src/components/run/RunModal.tsx

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { X, Play, Loader2 } from "lucide-react";

import { startRun } from "@/lib/api";
import type { Repo } from "@/types/agent";

interface RunModalProps {
  repo: Repo;
  onClose: () => void;
}

export default function RunModal({ repo, onClose }: RunModalProps) {
  const router = useRouter();

  const [teamName, setTeamName] = useState("");
  const [teamLeader, setTeamLeader] = useState("");
  const [maxIter, setMaxIter] = useState(5);
  const [readonly, setReadonly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!teamName.trim() || !teamLeader.trim()) {
      setError("Team name and team leader are required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await startRun({
        repo_url: repo.html_url,
        team_name: teamName.trim(),
        team_leader: teamLeader.trim(),
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
              Start a New Run
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

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Team Name
            </label>
            <input
              type="text"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="e.g. team-alpha"
              className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-zinc-600 transition-shadow"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Team Leader
            </label>
            <input
              type="text"
              value={teamLeader}
              onChange={(e) => setTeamLeader(e.target.value)}
              placeholder="e.g. rahulkpr2510"
              className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-zinc-600 transition-shadow"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Max Iterations
              <span className="ml-1.5 text-zinc-400 dark:text-zinc-600 font-normal">
                (1–10)
              </span>
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={maxIter}
              onChange={(e) => setMaxIter(Number(e.target.value))}
              className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-zinc-600 transition-shadow"
            />
          </div>

          <label className="flex items-center gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={readonly}
              onChange={(e) => setReadonly(e.target.checked)}
              className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 accent-zinc-900 dark:accent-white"
            />
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              Read-only mode{" "}
              <span className="text-zinc-400 dark:text-zinc-600">
                (analyse only, no commits)
              </span>
            </span>
          </label>

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
            {loading ? "Starting…" : "Start Run"}
          </button>
        </form>
      </div>
    </div>
  );
}
