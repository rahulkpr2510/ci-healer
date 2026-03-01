// frontend/src/app/repos/page.tsx

"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  GitBranch,
  Lock,
  Globe,
  RefreshCw,
  Play,
  Search,
  History,
} from "lucide-react";

import { getUserRepos } from "@/lib/api";
import type { Repo } from "@/types/agent";
import RunModal from "@/components/run/RunModal";

export default function ReposPage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [filtered, setFiltered] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Repo | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUserRepos();
      setRepos(data.repos ?? []);
      setFiltered(data.repos ?? []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!query.trim()) {
      setFiltered(repos);
      return;
    }
    const q = query.toLowerCase();
    setFiltered(repos.filter((r) => r.full_name.toLowerCase().includes(q)));
  }, [query, repos]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-white">
            Repositories
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-500 mt-0.5">
            Pick a repo to start a CI Healer run.
          </p>
        </div>
        <button
          onClick={load}
          className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-600"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search repositories…"
          className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg pl-9 pr-4 py-2 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-zinc-600 transition-shadow"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Repo list */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="px-5 py-4 flex gap-3 items-center">
                <div className="h-4 w-4 shimmer rounded" />
                <div className="h-4 w-48 shimmer rounded" />
                <div className="h-4 w-16 shimmer rounded ml-auto" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-zinc-400 dark:text-zinc-600">
            {query ? `No repos matching "${query}"` : "No repositories found."}
          </div>
        ) : (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {filtered.map((repo) => (
              <div
                key={repo.id}
                className="flex items-center gap-3 px-5 py-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors"
              >
                {/* Visibility icon */}
                <div className="shrink-0 text-zinc-400 dark:text-zinc-600">
                  {repo.private ? <Lock size={13} /> : <Globe size={13} />}
                </div>

                {/* Repo info */}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 truncate">
                    {repo.full_name}
                  </p>
                  <div className="flex items-center gap-3 mt-0.5">
                    {repo.language && (
                      <span className="text-xs text-zinc-400 dark:text-zinc-600">
                        {repo.language}
                      </span>
                    )}
                    {repo.description && (
                      <span className="text-xs text-zinc-400 dark:text-zinc-600 truncate">
                        {repo.description}
                      </span>
                    )}
                  </div>
                </div>

                {/* Branch + actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <span className="hidden sm:flex items-center gap-1 text-xs text-zinc-400 dark:text-zinc-600">
                    <GitBranch size={11} />
                    {repo.default_branch}
                  </span>
                  <Link
                    href={`/repo/${repo.owner}/${repo.name}`}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 text-xs font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800/50 hover:text-zinc-900 dark:hover:text-white transition-colors"
                    title="View run history"
                  >
                    <History size={11} />
                    <span className="hidden sm:block">History</span>
                  </Link>
                  <button
                    onClick={() => setSelected(repo)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 dark:bg-white border border-zinc-900 dark:border-white text-white dark:text-zinc-900 text-xs font-medium hover:bg-zinc-700 dark:hover:bg-zinc-100 transition-colors"
                  >
                    <Play size={11} />
                    Run
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run modal */}
      {selected && (
        <RunModal repo={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
