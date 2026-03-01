// frontend/src/store/agentStore.ts

import { create } from "zustand";
import type { Run, SSEEvent, User, RunStatus } from "@/types/agent";

interface AgentStore {
  // ── Auth ───────────────────────────────────────────────
  user: User | null;
  authLoading: boolean;
  setUser: (u: User | null) => void;
  setAuthLoading: (v: boolean) => void;

  // ── Active run ─────────────────────────────────────────
  activeRunId: string | null;
  activeRun: Run | null;
  runLoading: boolean;
  runError: string | null;
  logLines: SSEEvent[];

  setActiveRunId: (id: string | null) => void;
  setActiveRun: (r: Run | null) => void;
  setRunLoading: (v: boolean) => void;
  setRunError: (e: string | null) => void;

  appendLog: (e: SSEEvent) => void;
  clearLogs: () => void;
  resetRun: () => void;

  // convenience selector-like state
  runStatus: RunStatus | null;
}

export const useAgentStore = create<AgentStore>((set) => ({
  // ── Auth ───────────────────────────────────────────────
  user: null,
  authLoading: true,
  setUser: (user) => set({ user }),
  setAuthLoading: (authLoading) => set({ authLoading }),

  // ── Active run ─────────────────────────────────────────
  activeRunId: null,
  activeRun: null,
  runLoading: false,
  runError: null,
  logLines: [],

  setActiveRunId: (activeRunId) => set({ activeRunId }),
  setActiveRun: (activeRun) =>
    set({
      activeRun,
      runStatus: activeRun?.final_status ?? null,
    }),
  setRunLoading: (runLoading) => set({ runLoading }),
  setRunError: (runError) => set({ runError }),

  appendLog: (e) =>
    set((s) => ({
      logLines: [...s.logLines.slice(-199), e], // keep last 200
    })),
  clearLogs: () => set({ logLines: [] }),

  resetRun: () =>
    set({
      activeRunId: null,
      activeRun: null,
      runLoading: false,
      runError: null,
      logLines: [],
      runStatus: null,
    }),

  runStatus: null,
}));

// ── Selectors ──────────────────────────────────────────────
export const selectUser = (s: AgentStore) => s.user;
export const selectActiveRun = (s: AgentStore) => s.activeRun;
export const selectLogLines = (s: AgentStore) => s.logLines;
export const selectRunStatus = (s: AgentStore) => s.runStatus;
