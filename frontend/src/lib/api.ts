// frontend/src/lib/api.ts

import type {
  User,
  Run,
  RunSummary,
  Repo,
  RepoAnalytics,
  DashboardSummary,
  RunHistory,
  RunRequest,
  RunStartResponse,
  SSEEvent,
} from "@/types/agent";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_KEY = "cihealer_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };

  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/auth/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }

  // some endpoints may return empty body (204), guard it
  const text = await res.text();
  return (text ? JSON.parse(text) : ({} as T)) as T;
}

/* ───────────────────────── Auth ───────────────────────── */

export function getGithubLoginUrl(): string {
  return `${BASE_URL}/auth/github`;
}

/**
 * Pings the backend /warmup endpoint which simultaneously wakes the AI engine.
 * Call once on app load so both Render services are warm before the user
 * triggers a real run.
 */
export async function startupWarmup(): Promise<void> {
  try {
    await fetch(`${BASE_URL}/warmup`, { method: "GET" });
  } catch {
    // Non-fatal — services will wake up on first real request anyway
  }
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/auth/logout", { method: "POST" });
  clearToken();
}

/* ───────────────────────── Repos ──────────────────────── */

export async function getUserRepos(): Promise<{
  repos: Repo[];
  count: number;
}> {
  return apiFetch<{ repos: Repo[]; count: number }>("/api/repos");
}

/* ───────────────────────── Runs ───────────────────────── */

export async function startRun(payload: RunRequest): Promise<RunStartResponse> {
  return apiFetch<RunStartResponse>("/api/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getRun(runId: string): Promise<Run> {
  return apiFetch<Run>(`/api/run/${runId}`);
}

/**
 * SSE stream for /api/run/{runId}/events
 *
 * Note: EventSource cannot send custom headers, so the JWT is passed via
 * the ?token= query parameter. The backend middleware accepts it as a
 * fallback for browser-originated EventSource connections.
 *
 * The legacy /stream path is kept on the backend for backwards compatibility.
 */
export function streamRun(
  runId: string,
  onEvent: (e: SSEEvent) => void,
  onDone: () => void,
  onError?: (err: Event) => void,
): EventSource {
  const token = getToken();
  const qs = token ? `?token=${encodeURIComponent(token)}` : "";
  // Primary SSE path — /events (backend keeps /stream as a legacy alias)
  const es = new EventSource(`${BASE_URL}/api/run/${runId}/events${qs}`);

  es.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data) as SSEEvent;
      if (data.type === "ping") return;

      onEvent(data);

      if (data.type === "complete" || data.type === "error") {
        es.close();
        onDone();
      }
    } catch {
      // ignore malformed lines
    }
  };

  es.onerror = (e) => {
    onError?.(e);
    es.close();
    onDone();
  };

  return es;
}

/* ───────────────────────── History ────────────────────── */

export async function getRepoHistory(
  owner: string,
  repo: string,
  page = 1,
  pageSize = 20,
): Promise<RunHistory> {
  return apiFetch<RunHistory>(
    `/api/history/${owner}/${repo}?page=${page}&page_size=${pageSize}`,
  );
}

export async function getAllHistory(
  page = 1,
  pageSize = 20,
): Promise<{ runs: RunSummary[] }> {
  return apiFetch<{ runs: RunSummary[] }>(
    `/api/history/all?page=${page}&page_size=${pageSize}`,
  );
}

/* ───────────────────────── Analytics ──────────────────── */

export async function getRepoAnalytics(
  owner: string,
  repo: string,
): Promise<RepoAnalytics> {
  return apiFetch<RepoAnalytics>(`/api/analytics/${owner}/${repo}`);
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch<DashboardSummary>("/api/analytics/dashboard/summary");
}
