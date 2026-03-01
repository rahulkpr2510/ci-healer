export type RunStatus = "RUNNING" | "PASSED" | "FAILED";

export type BugType =
  | "LINTING"
  | "SYNTAX"
  | "LOGIC"
  | "TYPEERROR"
  | "IMPORT"
  | "INDENTATION";

export type FixStatus = "FIXED" | "FAILED" | "SKIPPED";

export interface User {
  id: number;
  github_id: number;
  github_username: string;
  github_email: string | null;
  github_avatar_url: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface ScoreBreakdown {
  base_score: number;
  speed_bonus: number;
  efficiency_penalty: number;
  final_score: number;
}

export interface Fix {
  file: string;
  bug_type: BugType;
  line_number: number;
  commit_message: string;
  status: FixStatus;
}

export interface CiEvent {
  iteration: number;
  status: RunStatus;
  iteration_label: string;
  ran_at: string | null;
}

export interface RunTiming {
  started_at: string | null;
  finished_at: string | null;
  total_time_seconds: number | null;
}

export interface Run {
  run_id: string;

  repo_url: string;
  repo_owner: string;
  repo_name: string;

  team_name: string;
  team_leader: string;

  mode: string;

  branch_name: string | null;
  pr_url: string | null;

  final_status: RunStatus;

  total_failures_detected: number;
  total_fixes_applied: number;
  total_commits: number;
  iterations_used: number;

  score: ScoreBreakdown;
  timing: RunTiming;

  fixes: Fix[];
  ci_timeline: CiEvent[];

  created_at: string;
}

export interface RunSummary {
  run_id: string;

  repo_owner: string;
  repo_name: string;
  repo_url: string;

  final_status: RunStatus;

  total_fixes_applied: number;
  final_score: number;

  total_time_seconds: number | null;
  started_at: string | null;
}

export interface Repo {
  id: number;
  full_name: string;
  owner: string;
  name: string;
  html_url: string;
  description: string | null;
  private: boolean;
  default_branch: string;
  updated_at: string;
  language: string | null;
}

export interface AnalyticsSummary {
  total_runs: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_time_seconds: number;
  avg_score: number;
  avg_fixes_per_run: number;
  total_fixes_ever: number;
}

export interface RepoAnalytics {
  owner: string;
  repo: string;
  summary: AnalyticsSummary;
  bug_type_distribution: Partial<Record<BugType, number>>;
  recent_runs: RunSummary[];
}

export interface DashboardSummary {
  total_runs: number;
  unique_repos: number;
  total_fixes_applied: number;
  pass_rate: number;
  repos: string[];
}

export interface RunHistory {
  owner: string;
  repo: string;
  total: number;
  page: number;
  page_size: number;
  runs: RunSummary[];
}

export interface RunRequest {
  repo_url: string;
  team_name: string;
  team_leader: string;
  max_iterations?: number;
  read_only?: boolean;
}

export interface RunStartResponse {
  run_id: string;
  status: string;
  message: string;
}

export type SSEEventType =
  | "log"
  | "complete"
  | "error"
  | "ping"
  // Semantic event types
  | "AGENT_STARTED"
  | "REPO_CLONED"
  | "TEST_DISCOVERED"
  | "TEST_FAILED"
  | "FIX_GENERATED"
  | "COMMIT_CREATED"
  | "CI_RERUN"
  | "RUN_COMPLETED";

export interface SSEEvent {
  type: SSEEventType;
  run_id?: string;
  level?: "info" | "success" | "warning" | "error";
  text?: string;
  message?: string;

  final_status?: RunStatus;

  node?: string;
  failures_count?: number;
  fixes_count?: number;
  latest_fix?: Partial<Fix>;

  // Additional fields for semantic events
  file?: string;
  bug_type?: string;
  line?: number;
  repo_url?: string;
  branch_name?: string;
  test_count?: number;
  commit_count?: number;
  iteration?: number;
  score?: number;
}
